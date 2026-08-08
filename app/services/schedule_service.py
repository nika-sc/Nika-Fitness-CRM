"""Group class schedule and bookings."""
from __future__ import annotations

from datetime import datetime, timedelta

from psycopg2.extras import RealDictCursor

from app.database.connection import execute, execute_returning, fetch_all, fetch_one, get_db_connection
from app.services.alert_service import AlertService
from app.services.membership_service import MembershipService
from app.services.settings_service import SettingsService


class ScheduleService:
    @staticmethod
    def list_types(active_only: bool = True) -> list[dict]:
        if active_only:
            return fetch_all('SELECT * FROM class_types WHERE is_active = TRUE ORDER BY name')
        return fetch_all('SELECT * FROM class_types ORDER BY name')

    @staticmethod
    def create_type(data: dict) -> dict:
        return execute_returning(
            """
            INSERT INTO class_types (name, description, default_price_cents, default_capacity)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (
                data['name'].strip(),
                (data.get('description') or '').strip(),
                int(round(float(data.get('price') or 0) * 100)),
                int(data.get('capacity') or 15),
            ),
        )

    @staticmethod
    def list_sessions(week_start: datetime | None = None) -> list[dict]:
        if week_start is None:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=7)
        return fetch_all(
            """
            SELECT s.*,
                   ct.name AS class_name,
                   t.full_name AS trainer_name,
                   (SELECT COUNT(*) FROM class_bookings b
                    WHERE b.session_id = s.id AND b.status = 'booked') AS booked_count
            FROM class_sessions s
            JOIN class_types ct ON ct.id = s.class_type_id
            LEFT JOIN trainers t ON t.id = s.trainer_id
            WHERE s.starts_at >= %s AND s.starts_at < %s
            ORDER BY s.starts_at
            """,
            (week_start, week_end),
        )

    @staticmethod
    def get_session(session_id: int) -> dict | None:
        return fetch_one(
            """
            SELECT s.*, ct.name AS class_name, t.full_name AS trainer_name
            FROM class_sessions s
            JOIN class_types ct ON ct.id = s.class_type_id
            LEFT JOIN trainers t ON t.id = s.trainer_id
            WHERE s.id = %s
            """,
            (session_id,),
        )

    @staticmethod
    def create_session(data: dict) -> dict:
        ctype = fetch_one('SELECT * FROM class_types WHERE id = %s', (int(data['class_type_id']),))
        if not ctype:
            raise ValueError('Тип занятия не найден')
        starts = datetime.fromisoformat(data['starts_at'])
        ends = datetime.fromisoformat(data['ends_at']) if data.get('ends_at') else starts + timedelta(hours=1)
        price = data.get('price')
        price_cents = int(round(float(price) * 100)) if price not in (None, '') else ctype['default_price_cents']
        capacity = int(data.get('capacity') or ctype['default_capacity'])
        trainer_id = int(data['trainer_id']) if data.get('trainer_id') else None
        return execute_returning(
            """
            INSERT INTO class_sessions
                (class_type_id, trainer_id, room_name, starts_at, ends_at, capacity, price_cents, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                ctype['id'],
                trainer_id,
                (data.get('room_name') or 'Зал 1').strip(),
                starts,
                ends,
                capacity,
                price_cents,
                (data.get('notes') or '').strip(),
            ),
        )

    @staticmethod
    def book(session_id: int, member_id: int, source: str = 'staff') -> dict:
        source = (source or 'staff').strip().lower()
        if source not in ('staff', 'portal', 'waitlist'):
            source = 'staff'

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT s.*, ct.name AS class_name
                    FROM class_sessions s
                    JOIN class_types ct ON ct.id = s.class_type_id
                    WHERE s.id = %s
                    FOR UPDATE OF s
                    """,
                    (session_id,),
                )
                session = cur.fetchone()
                if not session:
                    raise ValueError('Занятие не найдено')
                session = dict(session)

                cur.execute(
                    """
                    SELECT * FROM class_bookings
                    WHERE session_id = %s AND member_id = %s
                    FOR UPDATE
                    """,
                    (session_id, member_id),
                )
                existing = cur.fetchone()
                if existing and existing['status'] == 'booked':
                    row = dict(existing)
                    row['already_booked'] = True
                    row['class_name'] = session.get('class_name')
                    row['starts_at'] = session.get('starts_at')
                    return row

                cur.execute(
                    "SELECT COUNT(*)::int AS c FROM class_bookings WHERE session_id = %s AND status = 'booked'",
                    (session_id,),
                )
                booked = cur.fetchone()
                if booked and booked['c'] >= session['capacity']:
                    raise ValueError('Нет свободных мест')

                if existing:
                    cur.execute(
                        """
                        UPDATE class_bookings
                        SET status = 'booked',
                            source = %s,
                            updated_at = NOW(),
                            cancelled_at = NULL
                        WHERE id = %s
                        RETURNING *
                        """,
                        (source, existing['id']),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO class_bookings (session_id, member_id, status, source)
                        VALUES (%s, %s, 'booked', %s)
                        RETURNING *
                        """,
                        (session_id, member_id, source),
                    )
                booking = dict(cur.fetchone())
                booking['already_booked'] = False
                booking['class_name'] = session.get('class_name')
                booking['starts_at'] = session.get('starts_at')

                if source == 'portal':
                    cur.execute('SELECT full_name, card_number FROM members WHERE id = %s', (member_id,))
                    member = cur.fetchone() or {}
                    starts = session.get('starts_at')
                    when = starts.strftime('%d.%m %H:%M') if hasattr(starts, 'strftime') else str(starts)
                    cur.execute(
                        """
                        INSERT INTO staff_alerts (member_id, alert_type, title, body, severity)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            member_id,
                            'class_portal_booking',
                            f"Запись из ЛК · {member.get('full_name') or 'Клиент'}",
                            f"{session.get('class_name') or 'Занятие'} · {when} · {member.get('card_number') or ''}",
                            'info',
                        ),
                    )
                return booking

    @staticmethod
    def cancel_booking(booking_id: int, member_id: int | None = None, enforce_portal_window: bool = False) -> dict:
        booking = fetch_one(
            """
            SELECT b.*, s.starts_at, ct.name AS class_name
            FROM class_bookings b
            JOIN class_sessions s ON s.id = b.session_id
            JOIN class_types ct ON ct.id = s.class_type_id
            WHERE b.id = %s
            """,
            (booking_id,),
        )
        if not booking:
            raise ValueError('Запись не найдена')
        if booking['status'] != 'booked':
            raise ValueError('Запись уже не активна')
        if member_id is not None and int(booking['member_id']) != int(member_id):
            raise ValueError('Нельзя отменить чужую запись')

        if enforce_portal_window:
            hours = SettingsService.get_int('portal_cancel_before_hours', 2)
            starts = booking['starts_at']
            if isinstance(starts, str):
                starts = datetime.fromisoformat(starts)
            now = datetime.now(starts.tzinfo) if getattr(starts, 'tzinfo', None) else datetime.now()
            if starts - now < timedelta(hours=hours):
                raise ValueError(f'Отмена возможна не позднее чем за {hours} ч. до занятия')

        execute(
            """
            UPDATE class_bookings
            SET status = 'cancelled', cancelled_at = NOW(), updated_at = NOW()
            WHERE id = %s
            """,
            (booking_id,),
        )
        booking['status'] = 'cancelled'
        return booking

    @staticmethod
    def session_bookings(session_id: int) -> list[dict]:
        return fetch_all(
            """
            SELECT b.*, m.full_name, m.card_number
            FROM class_bookings b
            JOIN members m ON m.id = b.member_id
            WHERE b.session_id = %s AND b.status <> 'cancelled'
            ORDER BY b.created_at
            """,
            (session_id,),
        )

    @staticmethod
    def list_bookings_for_member(member_id: int, upcoming_only: bool = False, limit: int = 50) -> list[dict]:
        sql = """
            SELECT b.*, s.starts_at, s.ends_at, s.capacity, s.room_name,
                   ct.name AS class_name, t.full_name AS trainer_name
            FROM class_bookings b
            JOIN class_sessions s ON s.id = b.session_id
            JOIN class_types ct ON ct.id = s.class_type_id
            LEFT JOIN trainers t ON t.id = s.trainer_id
            WHERE b.member_id = %s
        """
        params: list = [member_id]
        if upcoming_only:
            sql += " AND b.status = 'booked' AND s.starts_at >= NOW()"
        sql += ' ORDER BY s.starts_at DESC LIMIT %s'
        params.append(limit)
        return fetch_all(sql, params)

    @staticmethod
    def recent_portal_bookings(hours: int = 24, limit: int = 30) -> list[dict]:
        return fetch_all(
            """
            SELECT b.*, m.full_name, m.card_number, s.starts_at, s.id AS session_id,
                   ct.name AS class_name
            FROM class_bookings b
            JOIN members m ON m.id = b.member_id
            JOIN class_sessions s ON s.id = b.session_id
            JOIN class_types ct ON ct.id = s.class_type_id
            WHERE b.source = 'portal'
              AND b.created_at >= NOW() - (%s || ' hours')::interval
            ORDER BY b.created_at DESC
            LIMIT %s
            """,
            (str(int(hours)), limit),
        )

    @staticmethod
    def today_sessions() -> list[dict]:
        return fetch_all(
            """
            SELECT s.*,
                   ct.name AS class_name,
                   t.full_name AS trainer_name,
                   (SELECT COUNT(*) FROM class_bookings b
                    WHERE b.session_id = s.id AND b.status = 'booked') AS booked_count
            FROM class_sessions s
            JOIN class_types ct ON ct.id = s.class_type_id
            LEFT JOIN trainers t ON t.id = s.trainer_id
            WHERE s.starts_at::date = CURRENT_DATE
            ORDER BY s.starts_at
            """
        )

    @staticmethod
    def booking_stats(days: int = 7) -> dict:
        row = fetch_one(
            """
            SELECT
              COUNT(*) FILTER (WHERE status = 'cancelled'
                AND COALESCE(cancelled_at, updated_at, created_at) >= NOW() - (%s || ' days')::interval)::int AS cancelled_week,
              COUNT(*) FILTER (WHERE status = 'no_show'
                AND COALESCE(updated_at, created_at) >= NOW() - (%s || ' days')::interval)::int AS noshow_week,
              COUNT(*) FILTER (WHERE source = 'portal'
                AND created_at >= NOW() - INTERVAL '24 hours')::int AS portal_24h
            FROM class_bookings
            """,
            (str(int(days)), str(int(days))),
        )
        return row or {'cancelled_week': 0, 'noshow_week': 0, 'portal_24h': 0}

    @staticmethod
    def mark_attended(booking_id: int) -> int:
        return execute(
            """
            UPDATE class_bookings
            SET status = 'attended', updated_at = NOW()
            WHERE id = %s AND status = 'booked'
            """,
            (booking_id,),
        )

    @staticmethod
    def mark_noshows(session_id: int) -> dict:
        session = ScheduleService.get_session(session_id)
        if not session:
            raise ValueError('Занятие не найдено')
        starts = session['starts_at']
        if isinstance(starts, str):
            starts = datetime.fromisoformat(starts)
        now = datetime.now(starts.tzinfo) if getattr(starts, 'tzinfo', None) else datetime.now()
        if starts > now:
            raise ValueError('Неявки можно отметить только после начала занятия')

        booked = fetch_all(
            """
            SELECT b.*, m.full_name, m.card_number
            FROM class_bookings b
            JOIN members m ON m.id = b.member_id
            WHERE b.session_id = %s AND b.status = 'booked'
            """,
            (session_id,),
        )
        if not booked:
            return {'marked': 0, 'deducted': 0}

        deduct = SettingsService.get_bool('noshow_deduct_visit', True)
        deducted = 0
        for row in booked:
            execute(
                "UPDATE class_bookings SET status = 'no_show', updated_at = NOW() WHERE id = %s",
                (row['id'],),
            )
            if deduct:
                membership = MembershipService.current_for_checkin(row['member_id'])
                if (
                    membership
                    and membership.get('visits_remaining') is not None
                    and membership['visits_remaining'] > 0
                ):
                    execute(
                        'UPDATE memberships SET visits_remaining = visits_remaining - 1, updated_at = NOW() WHERE id = %s',
                        (membership['id'],),
                    )
                    deducted += 1
            AlertService.create(
                alert_type='class_no_show',
                title=f"No-show · {row['full_name']}",
                body=f"{session.get('class_name') or 'Занятие'} · {row['card_number']}",
                severity='warning',
                member_id=row['member_id'],
            )
        return {'marked': len(booked), 'deducted': deducted}

    @staticmethod
    def fill_rates(week_start: datetime | None = None) -> list[dict]:
        sessions = ScheduleService.list_sessions(week_start)
        for s in sessions:
            cap = s['capacity'] or 1
            s['fill_pct'] = round(100.0 * (s.get('booked_count') or 0) / cap, 1)
        return sessions
