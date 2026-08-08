"""Segments, loyalty, NPS, leads."""
from __future__ import annotations

from app.database.connection import execute, execute_returning, fetch_all, fetch_one
from app.services.settings_service import SettingsService


class SegmentService:
    @staticmethod
    def list_segments() -> list[dict]:
        return fetch_all('SELECT * FROM segments ORDER BY id')

    @staticmethod
    def members_for_rule(rule_key: str) -> list[dict]:
        if rule_key == 'sleeping_14':
            return fetch_all(
                """
                SELECT m.* FROM members m
                WHERE m.status = 'active' AND NOT EXISTS (
                  SELECT 1 FROM checkins c WHERE c.member_id = m.id AND c.checked_at >= NOW() - INTERVAL '14 days'
                )
                ORDER BY m.full_name LIMIT 200
                """
            )
        if rule_key == 'sleeping_30':
            return fetch_all(
                """
                SELECT m.* FROM members m
                WHERE m.status = 'active' AND NOT EXISTS (
                  SELECT 1 FROM checkins c WHERE c.member_id = m.id AND c.checked_at >= NOW() - INTERVAL '30 days'
                )
                ORDER BY m.full_name LIMIT 200
                """
            )
        if rule_key == 'expiring_7':
            from app.services.membership_service import MembershipService
            return MembershipService.expiring_members(7)
        return []


class LoyaltyService:
    @staticmethod
    def get_account(member_id: int) -> dict:
        row = fetch_one('SELECT * FROM loyalty_accounts WHERE member_id = %s', (member_id,))
        if row:
            return row
        return execute_returning(
            'INSERT INTO loyalty_accounts (member_id, points) VALUES (%s, 0) RETURNING *',
            (member_id,),
        )

    @staticmethod
    def adjust(member_id: int, delta: int, reason: str, user_id: int | None = None) -> dict:
        LoyaltyService.get_account(member_id)
        execute(
            'UPDATE loyalty_accounts SET points = points + %s, updated_at = NOW() WHERE member_id = %s',
            (int(delta), member_id),
        )
        execute_returning(
            """
            INSERT INTO loyalty_ledger (member_id, delta, reason, created_by)
            VALUES (%s, %s, %s, %s) RETURNING id
            """,
            (member_id, int(delta), reason or '', user_id),
        )
        return LoyaltyService.get_account(member_id)

    @staticmethod
    def award_visit(member_id: int) -> None:
        pts = SettingsService.get_int('loyalty_points_per_visit', 1)
        if pts:
            LoyaltyService.adjust(member_id, pts, 'Визит')


class NpsService:
    @staticmethod
    def submit(member_id: int | None, score: int, comment: str = '') -> dict:
        score = int(score)
        if score < 0 or score > 10:
            raise ValueError('Оценка 0–10')
        return execute_returning(
            """
            INSERT INTO nps_responses (member_id, score, comment)
            VALUES (%s, %s, %s) RETURNING *
            """,
            (member_id, score, comment or ''),
        )

    @staticmethod
    def list_recent(limit: int = 100) -> list[dict]:
        return fetch_all(
            """
            SELECT n.*, m.full_name FROM nps_responses n
            LEFT JOIN members m ON m.id = n.member_id
            ORDER BY n.created_at DESC LIMIT %s
            """,
            (limit,),
        )


class LeadService:
    @staticmethod
    def list_all(status: str | None = None) -> list[dict]:
        if status:
            return fetch_all(
                """
                SELECT l.*, u.full_name AS assignee_name FROM leads l
                LEFT JOIN users u ON u.id = l.assigned_to
                WHERE l.status = %s ORDER BY l.updated_at DESC
                """,
                (status,),
            )
        return fetch_all(
            """
            SELECT l.*, u.full_name AS assignee_name FROM leads l
            LEFT JOIN users u ON u.id = l.assigned_to
            ORDER BY l.updated_at DESC LIMIT 300
            """
        )

    @staticmethod
    def create(data: dict) -> dict:
        return execute_returning(
            """
            INSERT INTO leads (full_name, phone, email, source, status, note, assigned_to)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *
            """,
            (
                data['full_name'].strip(),
                data.get('phone') or '',
                data.get('email') or '',
                data.get('source') or 'manual',
                data.get('status') or 'new',
                data.get('note') or '',
                int(data['assigned_to']) if data.get('assigned_to') else None,
            ),
        )

    @staticmethod
    def set_status(lead_id: int, status: str, assigned_to: int | None = None) -> dict:
        execute(
            """
            UPDATE leads SET status = %s,
              assigned_to = COALESCE(%s, assigned_to),
              updated_at = NOW()
            WHERE id = %s
            """,
            (status, assigned_to, lead_id),
        )
        return fetch_one('SELECT * FROM leads WHERE id = %s', (lead_id,))
