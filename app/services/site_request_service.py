"""Booking requests left on the public club site (no portal account needed).

A request never occupies a real seat: reception reviews it and confirms,
which is the moment a class booking or a trainer slot is actually created.
"""
from __future__ import annotations

import re

from app.database.connection import execute_returning, fetch_all, fetch_one
from app.services.alert_service import AlertService
from app.services.member_service import MemberService
from app.services.schedule_service import ScheduleService
from app.services.trainer_slot_service import TrainerSlotService
from app.services.waitlist_service import WaitlistService

KINDS = ('class', 'trainer', 'trial')
STATUSES = ('new', 'contacted', 'confirmed', 'declined', 'spam')
OPEN_STATUSES = ('new', 'contacted')

KIND_LABELS = {
    'class': 'Групповая тренировка',
    'trainer': 'Персональная тренировка',
    'trial': 'Пробное занятие',
}
STATUS_LABELS = {
    'new': 'Новая',
    'contacted': 'Связались',
    'confirmed': 'Записан',
    'declined': 'Отказ',
    'spam': 'Спам',
}

MAX_PER_PHONE_PER_DAY = 5
DEDUPE_MINUTES = 15
_NAME_RE = re.compile(r'^[^<>{}\\]{2,120}$')


def _clean_name(raw: str) -> str:
    name = re.sub(r'\s+', ' ', (raw or '').strip())[:120]
    if len(name) < 2 or not _NAME_RE.fullmatch(name):
        raise ValueError('Укажите имя')
    return name


def _clean_phone(raw: str) -> tuple[str, str]:
    """Return (display phone, comparable digits)."""
    phone = (raw or '').strip()[:40]
    digits = re.sub(r'\D+', '', phone)
    if not 10 <= len(digits) <= 15:
        raise ValueError('Укажите телефон в формате +7 900 000-00-00')
    return phone, digits[-10:]


class SiteRequestService:
    @staticmethod
    def kind_label(kind: str) -> str:
        return KIND_LABELS.get(kind, 'Заявка')

    @staticmethod
    def status_label(status: str) -> str:
        return STATUS_LABELS.get(status, status)

    # ----- public side -----
    @staticmethod
    def _describe_class(session_id: int) -> tuple[dict, str]:
        row = fetch_one(
            """
            SELECT s.id, s.starts_at, s.capacity, ct.name AS class_name,
                   t.id AS trainer_id, t.full_name AS trainer_name,
                   (SELECT COUNT(*) FROM class_bookings b
                    WHERE b.session_id = s.id AND b.status = 'booked')::int AS booked_count
            FROM class_sessions s
            JOIN class_types ct ON ct.id = s.class_type_id
            LEFT JOIN trainers t ON t.id = s.trainer_id
            WHERE s.id = %s AND s.starts_at > NOW()
            """,
            (session_id,),
        )
        if not row:
            raise ValueError('Занятие больше не доступно для записи')
        when = row['starts_at'].strftime('%d.%m %H:%M')
        label = f"{row['class_name']} · {when}"
        if row['booked_count'] >= row['capacity']:
            label += ' · лист ожидания'
        return row, label[:200]

    @staticmethod
    def _describe_slot(slot_id: int) -> tuple[dict, str]:
        row = fetch_one(
            """
            SELECT s.id, s.starts_at, s.trainer_id, t.full_name AS trainer_name
            FROM trainer_slots s
            JOIN trainers t ON t.id = s.trainer_id
            WHERE s.id = %s AND s.status = 'open' AND s.starts_at > NOW() AND t.is_active = TRUE
            """,
            (slot_id,),
        )
        if not row:
            raise ValueError('Это время уже занято, выберите другое')
        when = row['starts_at'].strftime('%d.%m %H:%M')
        return row, f"{row['trainer_name']} · {when}"[:200]

    @staticmethod
    def _describe_trainer(trainer_id: int) -> tuple[dict, str]:
        row = fetch_one(
            'SELECT id, full_name FROM trainers WHERE id = %s AND is_active = TRUE',
            (trainer_id,),
        )
        if not row:
            raise ValueError('Тренер не найден')
        return row, f"{row['full_name']} · время подберём"[:200]

    @staticmethod
    def create_public(data: dict) -> dict:
        kind = (data.get('kind') or 'trial').strip().lower()
        if kind not in KINDS:
            kind = 'trial'
        full_name = _clean_name(data.get('full_name'))
        phone, digits = _clean_phone(data.get('phone'))
        comment = re.sub(r'\s+', ' ', (data.get('comment') or '').strip())[:500]

        session_id = None
        slot_id = None
        trainer_id = None
        label = KIND_LABELS[kind]

        if kind == 'class':
            session, label = SiteRequestService._describe_class(int(data.get('session_id') or 0))
            session_id = session['id']
            trainer_id = session['trainer_id']
        elif kind == 'trainer':
            raw_slot = data.get('slot_id')
            if raw_slot:
                slot, label = SiteRequestService._describe_slot(int(raw_slot))
                slot_id = slot['id']
                trainer_id = slot['trainer_id']
            elif data.get('trainer_id'):
                trainer, label = SiteRequestService._describe_trainer(int(data['trainer_id']))
                trainer_id = trainer['id']

        recent = fetch_one(
            """
            SELECT COUNT(*)::int AS c FROM site_booking_requests
            WHERE RIGHT(regexp_replace(phone, '\\D', '', 'g'), 10) = %s
              AND created_at > NOW() - INTERVAL '1 day'
            """,
            (digits,),
        )
        if recent and recent['c'] >= MAX_PER_PHONE_PER_DAY:
            raise ValueError('Мы уже получили ваши заявки — скоро перезвоним')

        duplicate = fetch_one(
            """
            SELECT * FROM site_booking_requests
            WHERE RIGHT(regexp_replace(phone, '\\D', '', 'g'), 10) = %s
              AND kind = %s
              AND COALESCE(session_id, 0) = COALESCE(%s, 0)
              AND COALESCE(slot_id, 0) = COALESCE(%s, 0)
              AND COALESCE(trainer_id, 0) = COALESCE(%s, 0)
              AND created_at > NOW() - (%s * INTERVAL '1 minute')
            ORDER BY id DESC LIMIT 1
            """,
            (digits, kind, session_id, slot_id, trainer_id, DEDUPE_MINUTES),
        )
        if duplicate:
            return duplicate

        row = execute_returning(
            """
            INSERT INTO site_booking_requests
                (kind, session_id, slot_id, trainer_id, member_id,
                 full_name, phone, comment, target_label)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                kind,
                session_id,
                slot_id,
                trainer_id,
                SiteRequestService.match_member_id(digits),
                full_name,
                phone,
                comment,
                label,
            ),
        )
        AlertService.create(
            alert_type='site_booking_request',
            title=f'Заявка с сайта · {full_name}',
            body=f'{KIND_LABELS[kind]} · {label} · {phone}',
            severity='warning',
            member_id=row.get('member_id'),
        )
        return row

    # ----- staff side -----
    @staticmethod
    def match_member_id(digits: str) -> int | None:
        row = fetch_one(
            """
            SELECT id FROM members
            WHERE RIGHT(regexp_replace(phone, '\\D', '', 'g'), 10) = %s
            ORDER BY id LIMIT 1
            """,
            (digits,),
        )
        return int(row['id']) if row else None

    @staticmethod
    def list_all(status: str | None = None, limit: int = 200) -> list[dict]:
        sql = """
            SELECT r.*,
                   m.full_name AS member_name, m.card_number AS member_card,
                   t.full_name AS trainer_name,
                   u.full_name AS processed_by_name,
                   s.starts_at AS session_starts_at,
                   ((SELECT COUNT(*) FROM class_bookings b
                     WHERE b.session_id = s.id AND b.status = 'booked') >= s.capacity) AS session_full,
                   sl.starts_at AS slot_starts_at,
                   sl.status AS slot_status
            FROM site_booking_requests r
            LEFT JOIN members m ON m.id = r.member_id
            LEFT JOIN trainers t ON t.id = r.trainer_id
            LEFT JOIN users u ON u.id = r.processed_by
            LEFT JOIN class_sessions s ON s.id = r.session_id
            LEFT JOIN trainer_slots sl ON sl.id = r.slot_id
        """
        params: list = []
        if status == 'open':
            sql += ' WHERE r.status IN %s'
            params.append(OPEN_STATUSES)
        elif status in STATUSES:
            sql += ' WHERE r.status = %s'
            params.append(status)
        sql += ' ORDER BY r.created_at DESC LIMIT %s'
        params.append(int(limit))
        return fetch_all(sql, params)

    @staticmethod
    def counts() -> dict:
        row = fetch_one(
            """
            SELECT
              COUNT(*) FILTER (WHERE status = 'new')::int AS new,
              COUNT(*) FILTER (WHERE status = 'contacted')::int AS contacted,
              COUNT(*) FILTER (WHERE status = 'confirmed')::int AS confirmed,
              COUNT(*) FILTER (WHERE status IN ('declined', 'spam'))::int AS closed
            FROM site_booking_requests
            """
        )
        return dict(row) if row else {'new': 0, 'contacted': 0, 'confirmed': 0, 'closed': 0}

    @staticmethod
    def new_count() -> int:
        row = fetch_one("SELECT COUNT(*)::int AS c FROM site_booking_requests WHERE status = 'new'")
        return int(row['c']) if row else 0

    @staticmethod
    def get(request_id: int) -> dict | None:
        return fetch_one('SELECT * FROM site_booking_requests WHERE id = %s', (request_id,))

    @staticmethod
    def set_status(request_id: int, status: str, user_id: int | None = None) -> dict:
        if status not in STATUSES:
            raise ValueError('Недопустимый статус заявки')
        row = execute_returning(
            """
            UPDATE site_booking_requests
            SET status = %s, processed_by = %s, processed_at = NOW(), updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (status, user_id, request_id),
        )
        if not row:
            raise ValueError('Заявка не найдена')
        return row

    @staticmethod
    def save_note(request_id: int, note: str) -> dict:
        row = execute_returning(
            """
            UPDATE site_booking_requests
            SET staff_note = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            ((note or '').strip()[:500], request_id),
        )
        if not row:
            raise ValueError('Заявка не найдена')
        return row

    @staticmethod
    def create_member_from_request(request_id: int) -> dict:
        req = SiteRequestService.get(request_id)
        if not req:
            raise ValueError('Заявка не найдена')
        if req['member_id']:
            raise ValueError('Клиент уже привязан к заявке')
        member = MemberService.create({
            'full_name': req['full_name'],
            'phone': req['phone'],
            'notes': f"Заявка с сайта: {req['target_label']}",
        })
        execute_returning(
            'UPDATE site_booking_requests SET member_id = %s, updated_at = NOW() WHERE id = %s RETURNING id',
            (member['id'], request_id),
        )
        return member

    @staticmethod
    def link_member(request_id: int, member_id: int) -> dict:
        member = MemberService.get(member_id)
        if not member:
            raise ValueError('Клиент не найден')
        row = execute_returning(
            'UPDATE site_booking_requests SET member_id = %s, updated_at = NOW() WHERE id = %s RETURNING *',
            (member_id, request_id),
        )
        if not row:
            raise ValueError('Заявка не найдена')
        return row

    @staticmethod
    def session_is_full(session_id: int) -> bool:
        row = fetch_one(
            """
            SELECT s.capacity,
                   (SELECT COUNT(*) FROM class_bookings b
                    WHERE b.session_id = s.id AND b.status = 'booked')::int AS booked
            FROM class_sessions s WHERE s.id = %s
            """,
            (session_id,),
        )
        if not row:
            raise ValueError('Занятие больше не существует')
        return int(row['booked']) >= int(row['capacity'])

    @staticmethod
    def confirm(request_id: int, user_id: int | None = None) -> dict:
        """Turn an approved request into a real booking (or a waitlist spot)."""
        req = SiteRequestService.get(request_id)
        if not req:
            raise ValueError('Заявка не найдена')
        if req['status'] == 'confirmed':
            raise ValueError('Заявка уже подтверждена')
        member_id = req['member_id']
        if not member_id:
            raise ValueError('Сначала привяжите клиента или создайте карточку')

        outcome = 'confirmed'
        if req['kind'] == 'class' and req['session_id']:
            if SiteRequestService.session_is_full(req['session_id']):
                WaitlistService.join(req['session_id'], member_id)
                outcome = 'waitlisted'
            else:
                try:
                    ScheduleService.book(req['session_id'], member_id, source='staff')
                    outcome = 'booked'
                except ValueError:
                    # last seat taken between the check and the insert
                    WaitlistService.join(req['session_id'], member_id)
                    outcome = 'waitlisted'
        elif req['kind'] == 'trainer' and req['slot_id']:
            TrainerSlotService.book(req['slot_id'], member_id, source='staff')
            outcome = 'booked'

        row = SiteRequestService.set_status(request_id, 'confirmed', user_id)
        row['outcome'] = outcome
        return row
