"""In-CRM staff alerts visible to all users."""
from __future__ import annotations

from app.database.connection import execute, execute_returning, fetch_all, fetch_one


class AlertService:
    @staticmethod
    def create(
        alert_type: str,
        title: str,
        body: str = '',
        severity: str = 'warning',
        member_id: int | None = None,
        checkin_id: int | None = None,
    ) -> dict:
        return execute_returning(
            """
            INSERT INTO staff_alerts (member_id, checkin_id, alert_type, title, body, severity)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (member_id, checkin_id, alert_type, title, body, severity),
        )

    @staticmethod
    def list_recent(limit: int = 50) -> list[dict]:
        return fetch_all(
            """
            SELECT a.*, m.full_name, m.card_number
            FROM staff_alerts a
            LEFT JOIN members m ON m.id = a.member_id
            ORDER BY a.created_at DESC
            LIMIT %s
            """,
            (limit,),
        )

    @staticmethod
    def unread_count() -> int:
        row = fetch_one('SELECT COUNT(*)::int AS c FROM staff_alerts WHERE is_read = FALSE')
        return int(row['c']) if row else 0

    @staticmethod
    def mark_all_read() -> int:
        return execute('UPDATE staff_alerts SET is_read = TRUE WHERE is_read = FALSE')

    @staticmethod
    def mark_read(alert_id: int) -> int:
        return execute('UPDATE staff_alerts SET is_read = TRUE WHERE id = %s', (alert_id,))
