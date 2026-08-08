"""Class waitlist."""
from __future__ import annotations

from app.database.connection import execute, execute_returning, fetch_all, fetch_one
from app.services.message_service import MessageService
from app.services.member_service import MemberService
from app.services.schedule_service import ScheduleService


class WaitlistService:
    @staticmethod
    def list_for_session(session_id: int) -> list[dict]:
        return fetch_all(
            """
            SELECT w.*, m.full_name, m.card_number, m.phone
            FROM class_waitlist w
            JOIN members m ON m.id = w.member_id
            WHERE w.session_id = %s AND w.status = 'waiting'
            ORDER BY w.position, w.id
            """,
            (session_id,),
        )

    @staticmethod
    def join(session_id: int, member_id: int) -> dict:
        existing = fetch_one(
            'SELECT * FROM class_waitlist WHERE session_id = %s AND member_id = %s',
            (session_id, member_id),
        )
        if existing and existing['status'] == 'waiting':
            return existing
        max_pos = fetch_one(
            "SELECT COALESCE(MAX(position), 0)::int AS p FROM class_waitlist WHERE session_id = %s AND status = 'waiting'",
            (session_id,),
        )
        pos = (max_pos['p'] if max_pos else 0) + 1
        if existing:
            execute(
                "UPDATE class_waitlist SET status = 'waiting', position = %s, notified_at = NULL WHERE id = %s",
                (pos, existing['id']),
            )
            return fetch_one('SELECT * FROM class_waitlist WHERE id = %s', (existing['id'],))
        return execute_returning(
            """
            INSERT INTO class_waitlist (session_id, member_id, position, status)
            VALUES (%s, %s, %s, 'waiting') RETURNING *
            """,
            (session_id, member_id, pos),
        )

    @staticmethod
    def promote_next(session_id: int) -> dict | None:
        row = fetch_one(
            """
            SELECT w.*, m.full_name, m.phone, m.email
            FROM class_waitlist w
            JOIN members m ON m.id = w.member_id
            WHERE w.session_id = %s AND w.status = 'waiting'
            ORDER BY w.position, w.id LIMIT 1
            """,
            (session_id,),
        )
        if not row:
            return None
        try:
            ScheduleService.book(session_id, row['member_id'], source='waitlist')
        except Exception:
            return None
        execute(
            "UPDATE class_waitlist SET status = 'promoted', notified_at = NOW() WHERE id = %s",
            (row['id'],),
        )
        if row.get('phone'):
            MessageService.send('sms', row['phone'], 'waitlist_promoted', {'session_id': session_id})
        return row
