"""Personal training slots: trainer opens windows, clients take them."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.database.connection import execute_returning, fetch_all, fetch_one
from app.services.alert_service import AlertService
from app.services.settings_service import SettingsService

SLOT_STATUSES = ('open', 'pending', 'booked', 'done', 'no_show', 'cancelled')
ACTIVE_STATUSES = ('pending', 'booked')
MAX_SLOTS_PER_REQUEST = 60


def _as_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _now_like(moment: datetime) -> datetime:
    tz = getattr(moment, 'tzinfo', None)
    return datetime.now(tz) if tz else datetime.now()


class TrainerSlotService:
    @staticmethod
    def list_for_trainer(trainer_id: int, start: date, end: date) -> list[dict]:
        return fetch_all(
            """
            SELECT s.*, m.full_name AS member_name, m.phone AS member_phone,
                   m.card_number AS member_card
            FROM trainer_slots s
            LEFT JOIN members m ON m.id = s.member_id
            WHERE s.trainer_id = %s
              AND s.starts_at >= %s AND s.starts_at < %s
            ORDER BY s.starts_at
            """,
            (trainer_id, start, end + timedelta(days=1)),
        )

    @staticmethod
    def list_open(trainer_id: int | None = None, days: int = 14, limit: int = 200) -> list[dict]:
        sql = """
            SELECT s.*, t.full_name AS trainer_name, t.photo_path AS trainer_photo
            FROM trainer_slots s
            JOIN trainers t ON t.id = s.trainer_id
            WHERE s.status = 'open'
              AND t.is_active = TRUE
              AND s.starts_at > NOW()
              AND s.starts_at < NOW() + (%s * INTERVAL '1 day')
        """
        params: list = [int(days)]
        if trainer_id:
            sql += ' AND s.trainer_id = %s'
            params.append(int(trainer_id))
        sql += ' ORDER BY s.starts_at LIMIT %s'
        params.append(int(limit))
        return fetch_all(sql, params)

    @staticmethod
    def list_for_member(member_id: int, upcoming_only: bool = True, limit: int = 50) -> list[dict]:
        sql = """
            SELECT s.*, t.full_name AS trainer_name
            FROM trainer_slots s
            JOIN trainers t ON t.id = s.trainer_id
            WHERE s.member_id = %s AND s.status IN ('pending', 'booked', 'done', 'no_show')
        """
        params: list = [int(member_id)]
        if upcoming_only:
            sql += " AND s.status IN ('pending', 'booked') AND s.starts_at > NOW()"
        sql += ' ORDER BY s.starts_at LIMIT %s'
        params.append(int(limit))
        return fetch_all(sql, params)

    @staticmethod
    def active_count_for_member(member_id: int) -> int:
        row = fetch_one(
            """
            SELECT COUNT(*)::int AS c FROM trainer_slots
            WHERE member_id = %s AND status IN ('pending', 'booked') AND starts_at > NOW()
            """,
            (member_id,),
        )
        return int(row['c']) if row else 0

    @staticmethod
    def get(slot_id: int) -> dict | None:
        return fetch_one(
            """
            SELECT s.*, t.full_name AS trainer_name, m.full_name AS member_name
            FROM trainer_slots s
            JOIN trainers t ON t.id = s.trainer_id
            LEFT JOIN members m ON m.id = s.member_id
            WHERE s.id = %s
            """,
            (slot_id,),
        )

    @staticmethod
    def create(
        trainer_id: int,
        slot_date: str,
        start_time: str,
        duration_min: int = 60,
        repeat_weekdays: list[int] | None = None,
        repeat_until: str | None = None,
        place: str = '',
        created_by: int | None = None,
    ) -> list[dict]:
        duration = int(duration_min or 60)
        if duration < 15 or duration > 480:
            raise ValueError('Длительность от 15 до 480 минут')
        try:
            first_day = date.fromisoformat(slot_date)
            hour, minute = (int(part) for part in str(start_time).split(':')[:2])
            begin = time(hour, minute)
        except (TypeError, ValueError):
            raise ValueError('Укажите корректные дату и время')

        days = [first_day]
        if repeat_weekdays:
            wanted = {int(d) for d in repeat_weekdays if str(d).isdigit()}
            if not repeat_until:
                raise ValueError('Для повтора укажите дату окончания')
            try:
                last_day = date.fromisoformat(repeat_until)
            except ValueError:
                raise ValueError('Некорректная дата окончания повтора')
            if last_day < first_day:
                raise ValueError('Дата окончания раньше начала')
            days = []
            cursor = first_day
            while cursor <= last_day:
                if cursor.weekday() in wanted:
                    days.append(cursor)
                cursor += timedelta(days=1)
            if not days:
                raise ValueError('Не выбрано ни одного дня недели')
        if len(days) > MAX_SLOTS_PER_REQUEST:
            raise ValueError(f'Слишком много окон за раз (максимум {MAX_SLOTS_PER_REQUEST})')

        created: list[dict] = []
        for day in days:
            starts = datetime.combine(day, begin)
            ends = starts + timedelta(minutes=duration)
            if starts < datetime.now():
                continue
            overlap = fetch_one(
                """
                SELECT id FROM trainer_slots
                WHERE trainer_id = %s
                  AND status <> 'cancelled'
                  AND starts_at < %s AND ends_at > %s
                LIMIT 1
                """,
                (trainer_id, ends, starts),
            )
            if overlap:
                continue
            row = execute_returning(
                """
                INSERT INTO trainer_slots (trainer_id, starts_at, ends_at, place, created_by)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (trainer_id, starts, ends, (place or '').strip()[:120], created_by),
            )
            if row:
                created.append(row)
        if not created:
            raise ValueError('Новые окна не созданы: время в прошлом или уже занято')
        return created

    @staticmethod
    def book(slot_id: int, member_id: int, source: str = 'staff') -> dict:
        """Portal requests wait for the trainer; desk and trainer bookings are final."""
        src = (source or 'staff').strip().lower()
        if src not in ('trainer', 'staff', 'portal'):
            src = 'staff'
        member = fetch_one('SELECT id, full_name, card_number FROM members WHERE id = %s', (member_id,))
        if not member:
            raise ValueError('Клиент не найден')

        limit = SettingsService.get_int('pt_max_active_bookings', 3)
        if limit > 0 and TrainerSlotService.active_count_for_member(member_id) >= limit:
            raise ValueError(
                f'У клиента уже {limit} незакрытых записей к тренеру. '
                'Сначала проведите или отмените их.'
            )

        new_status = 'pending' if src == 'portal' else 'booked'
        slot = execute_returning(
            """
            UPDATE trainer_slots
            SET status = %s, member_id = %s, source = %s,
                booked_at = NOW(),
                confirmed_at = CASE WHEN %s = 'booked' THEN NOW() ELSE NULL END,
                updated_at = NOW()
            WHERE id = %s AND status = 'open' AND starts_at > NOW()
            RETURNING *
            """,
            (new_status, member_id, src, new_status, slot_id),
        )
        if not slot:
            current = fetch_one('SELECT status FROM trainer_slots WHERE id = %s', (slot_id,))
            if not current:
                raise ValueError('Слот не найден')
            if current['status'] == 'open':
                raise ValueError('Слот уже прошёл')
            raise ValueError('Слот уже занят')

        trainer = fetch_one('SELECT full_name FROM trainers WHERE id = %s', (slot['trainer_id'],))
        starts = slot['starts_at']
        when = starts.strftime('%d.%m %H:%M') if hasattr(starts, 'strftime') else str(starts)
        if src == 'portal':
            AlertService.create(
                alert_type='pt_slot_request',
                title=f"Заявка на персоналку · {member['full_name']}",
                body=f"{trainer['full_name'] if trainer else 'Тренер'} · {when} · ждёт подтверждения",
                severity='warning',
                member_id=member_id,
            )
        slot['trainer_name'] = trainer['full_name'] if trainer else ''
        slot['member_name'] = member['full_name']
        return slot

    @staticmethod
    def confirm(slot_id: int) -> dict:
        slot = execute_returning(
            """
            UPDATE trainer_slots
            SET status = 'booked', confirmed_at = NOW(), updated_at = NOW()
            WHERE id = %s AND status = 'pending'
            RETURNING *
            """,
            (slot_id,),
        )
        if not slot:
            raise ValueError('Заявка не найдена или уже обработана')
        member = fetch_one('SELECT full_name FROM members WHERE id = %s', (slot['member_id'],))
        starts = slot['starts_at']
        when = starts.strftime('%d.%m %H:%M') if hasattr(starts, 'strftime') else str(starts)
        AlertService.create(
            alert_type='pt_slot_confirmed',
            title=f"Персоналка подтверждена · {member['full_name'] if member else 'Клиент'}",
            body=when,
            severity='info',
            member_id=slot['member_id'],
        )
        return slot

    @staticmethod
    def decline(slot_id: int, reason: str = '') -> dict:
        previous = fetch_one(
            'SELECT member_id, starts_at FROM trainer_slots WHERE id = %s AND status = %s',
            (slot_id, 'pending'),
        )
        slot = execute_returning(
            """
            UPDATE trainer_slots
            SET status = 'open', member_id = NULL, source = 'trainer',
                booked_at = NULL, confirmed_at = NULL, updated_at = NOW()
            WHERE id = %s AND status = 'pending'
            RETURNING *
            """,
            (slot_id,),
        )
        if not slot or not previous:
            raise ValueError('Заявка не найдена или уже обработана')
        starts = slot['starts_at']
        when = starts.strftime('%d.%m %H:%M') if hasattr(starts, 'strftime') else str(starts)
        note = (reason or '').strip()
        AlertService.create(
            alert_type='pt_slot_declined',
            title='Заявка на персоналку отклонена',
            body=f"{when}{' · ' + note if note else ''}",
            severity='warning',
            member_id=previous['member_id'],
        )
        return slot

    @staticmethod
    def cancel_booking(
        slot_id: int,
        member_id: int | None = None,
        enforce_portal_window: bool = False,
    ) -> dict:
        slot = fetch_one('SELECT * FROM trainer_slots WHERE id = %s', (slot_id,))
        if not slot:
            raise ValueError('Слот не найден')
        if slot['status'] not in ACTIVE_STATUSES:
            raise ValueError('Запись уже не активна')
        if member_id is not None and int(slot['member_id'] or 0) != int(member_id):
            raise ValueError('Нельзя отменить чужую запись')

        if enforce_portal_window and slot['status'] == 'booked':
            hours = SettingsService.get_int('portal_cancel_before_hours', 2)
            starts = _as_datetime(slot['starts_at'])
            if starts - _now_like(starts) < timedelta(hours=hours):
                raise ValueError(f'Отмена возможна не позднее чем за {hours} ч. до тренировки')

        return execute_returning(
            """
            UPDATE trainer_slots
            SET status = 'open', member_id = NULL, source = 'trainer',
                booked_at = NULL, confirmed_at = NULL, updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (slot_id,),
        )

    @staticmethod
    def mark(slot_id: int, status: str) -> dict:
        if status not in ('done', 'no_show'):
            raise ValueError('Недопустимый статус')
        slot = fetch_one('SELECT * FROM trainer_slots WHERE id = %s', (slot_id,))
        if not slot:
            raise ValueError('Слот не найден')
        if slot['status'] == 'pending':
            raise ValueError('Сначала подтвердите заявку клиента')
        if slot['status'] not in ('booked', 'done', 'no_show'):
            raise ValueError('Отметить можно только занятый слот')
        return execute_returning(
            'UPDATE trainer_slots SET status = %s, updated_at = NOW() WHERE id = %s RETURNING *',
            (status, slot_id),
        )

    @staticmethod
    def close(slot_id: int) -> dict:
        slot = fetch_one('SELECT * FROM trainer_slots WHERE id = %s', (slot_id,))
        if not slot:
            raise ValueError('Слот не найден')
        if slot['status'] in ACTIVE_STATUSES:
            raise ValueError('Сначала отмените запись клиента')
        return execute_returning(
            "UPDATE trainer_slots SET status = 'cancelled', updated_at = NOW() WHERE id = %s RETURNING *",
            (slot_id,),
        )

    @staticmethod
    def stats_for_trainer(trainer_id: int) -> dict:
        row = fetch_one(
            """
            SELECT
              COUNT(*) FILTER (WHERE status = 'open' AND starts_at > NOW())::int AS open_slots,
              COUNT(*) FILTER (WHERE status = 'pending' AND starts_at > NOW())::int AS pending_slots,
              COUNT(*) FILTER (WHERE status = 'booked' AND starts_at > NOW())::int AS booked_slots,
              COUNT(*) FILTER (WHERE status = 'done'
                               AND starts_at >= date_trunc('month', NOW()))::int AS done_month
            FROM trainer_slots
            WHERE trainer_id = %s
            """,
            (trainer_id,),
        )
        return {
            'open_slots': int(row['open_slots']) if row else 0,
            'pending_slots': int(row['pending_slots']) if row else 0,
            'booked_slots': int(row['booked_slots']) if row else 0,
            'done_month': int(row['done_month']) if row else 0,
        }
