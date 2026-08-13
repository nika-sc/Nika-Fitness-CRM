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

    @staticmethod
    def send_class_push(hours: int | None = None) -> int:
        from app.services.growth_service import PushService
        from app.services.settings_service import SettingsService

        window = hours if hours is not None else (SettingsService.get_int('class_reminder_hours', 3) or 3)
        rows = fetch_all(
            """
            SELECT DISTINCT ON (b.member_id, b.session_id)
                   b.member_id, s.starts_at, ct.name AS class_name
            FROM class_bookings b
            JOIN class_sessions s ON s.id = b.session_id
            JOIN class_types ct ON ct.id = s.class_type_id
            WHERE b.status = 'booked'
              AND s.starts_at BETWEEN NOW() AND NOW() + (%s * INTERVAL '1 hour')
            ORDER BY b.member_id, b.session_id, s.starts_at
            """,
            (window,),
        )
        sent = 0
        for row in rows:
            PushService.notify_member(
                row['member_id'],
                'class_reminder',
                {
                    'class_name': row.get('class_name'),
                    'starts_at': str(row.get('starts_at') or ''),
                },
            )
            sent += 1
        return sent
