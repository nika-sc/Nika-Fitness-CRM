"""Batch membership expiry email reminders."""
from __future__ import annotations

from datetime import date

from app.database.connection import execute, fetch_all
from app.services.membership_service import MembershipService
from app.services.notification_service import NotificationService


class ReminderService:
    @staticmethod
    def send_expiring_emails(days: int | None = None) -> int:
        rows = MembershipService.expiring_members(days=days)
        sent = 0
        for row in rows:
            email = (row.get('email') or '').strip()
            if not email:
                continue
            key = f"expiring_{row['ends_on']}"
            existing = fetch_all(
                'SELECT id FROM email_reminders WHERE membership_id = %s AND reminder_key = %s',
                (row['membership_id'], key),
            )
            if existing:
                continue
            days_left = (row['ends_on'] - date.today()).days
            ok = NotificationService.membership_expiring(row, row, days_left)
            if ok:
                execute(
                    """
                    INSERT INTO email_reminders (member_id, membership_id, reminder_key)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (row['id'], row['membership_id'], key),
                )
                sent += 1
        return sent
