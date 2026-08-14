"""Membership plans, memberships, payments."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from flask import current_app

from app.database.connection import execute, execute_returning, fetch_all, fetch_one
from app.services.settings_service import SettingsService


def _expiring_days() -> int:
    try:
        return int(current_app.config.get('MEMBERSHIP_EXPIRING_DAYS', 7))
    except Exception:
        return 7


class MembershipService:
    @staticmethod
    def compute_status(ends_on, visits_remaining=None, status: str | None = None) -> str:
        if status == 'frozen':
            return 'frozen'
        if isinstance(ends_on, datetime):
            ends = ends_on.date()
        else:
            ends = ends_on
        today = date.today()
        if visits_remaining is not None and visits_remaining <= 0:
            return 'expired'
        if ends < today:
            return 'expired'
        if ends <= today + timedelta(days=_expiring_days()):
            return 'expiring'
        return 'active'

    @staticmethod
    def list_plans(active_only: bool = True) -> list[dict]:
        if active_only:
            return fetch_all(
                'SELECT * FROM membership_plans WHERE is_active = TRUE ORDER BY price_cents'
            )
        return fetch_all('SELECT * FROM membership_plans ORDER BY id')

    @staticmethod
    def create_plan(data: dict) -> dict:
        visit_limit = data.get('visit_limit')
        if visit_limit in ('', None):
            visit_limit = None
        else:
            visit_limit = int(visit_limit)
        return execute_returning(
            """
            INSERT INTO membership_plans (name, description, duration_days, visit_limit, price_cents)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                data['name'].strip(),
                (data.get('description') or '').strip(),
                int(data.get('duration_days') or 30),
                visit_limit,
                int(round(float(data.get('price') or 0) * 100)),
            ),
        )

    @staticmethod
    def list_for_member(member_id: int) -> list[dict]:
        rows = fetch_all(
            """
            SELECT m.*, p.name AS plan_name, p.price_cents AS plan_price_cents
            FROM memberships m
            LEFT JOIN membership_plans p ON p.id = m.plan_id
            WHERE m.member_id = %s
            ORDER BY m.ends_on DESC
            """,
            (member_id,),
        )
        for row in rows:
            row['computed_status'] = MembershipService.compute_status(
                row['ends_on'], row.get('visits_remaining'), row.get('status')
            )
        return rows

    @staticmethod
    def current_for_member(member_id: int) -> dict | None:
        """Current membership for display (includes frozen)."""
        rows = MembershipService.list_for_member(member_id)
        for row in rows:
            if row['computed_status'] in ('active', 'expiring', 'frozen'):
                return row
        return rows[0] if rows else None

    @staticmethod
    def current_for_checkin(member_id: int) -> dict | None:
        """Membership usable for check-in (excludes frozen)."""
        rows = MembershipService.list_for_member(member_id)
        for row in rows:
            if row['computed_status'] in ('active', 'expiring'):
                return row
        return None

    @staticmethod
    def get_membership(membership_id: int) -> dict | None:
        row = fetch_one(
            """
            SELECT m.*, p.name AS plan_name
            FROM memberships m
            LEFT JOIN membership_plans p ON p.id = m.plan_id
            WHERE m.id = %s
            """,
            (membership_id,),
        )
        if row:
            row['computed_status'] = MembershipService.compute_status(
                row['ends_on'], row.get('visits_remaining'), row.get('status')
            )
        return row

    @staticmethod
    def active_freeze(membership_id: int) -> dict | None:
        return fetch_one(
            """
            SELECT * FROM membership_freezes
            WHERE membership_id = %s AND ends_on IS NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (membership_id,),
        )

    @staticmethod
    def freeze_days_used_this_year(membership_id: int, year: int | None = None) -> int:
        y = year or date.today().year
        row = fetch_one(
            """
            SELECT COALESCE(SUM(
                CASE
                    WHEN ends_on IS NULL THEN GREATEST(1, (CURRENT_DATE - starts_on))
                    ELSE days_used
                END
            ), 0)::int AS days
            FROM membership_freezes
            WHERE membership_id = %s
              AND EXTRACT(YEAR FROM starts_on) = %s
            """,
            (membership_id, y),
        )
        return int(row['days']) if row else 0

    @staticmethod
    def freeze(membership_id: int, reason: str, created_by: int | None = None) -> dict:
        membership = MembershipService.get_membership(membership_id)
        if not membership:
            raise ValueError('Абонемент не найден')
        if membership.get('status') == 'frozen':
            raise ValueError('Абонемент уже заморожен')
        computed = membership['computed_status']
        if computed == 'expired':
            raise ValueError('Нельзя заморозить истёкший абонемент')

        max_days = SettingsService.get_int('freeze_max_days_per_year', 30)
        used = MembershipService.freeze_days_used_this_year(membership_id)
        if used >= max_days:
            raise ValueError(f'Лимит заморозки на год исчерпан ({max_days} дн.)')

        freeze = execute_returning(
            """
            INSERT INTO membership_freezes (membership_id, starts_on, reason, created_by)
            VALUES (%s, CURRENT_DATE, %s, %s)
            RETURNING *
            """,
            (membership_id, (reason or '').strip(), created_by),
        )
        execute(
            "UPDATE memberships SET status = 'frozen', updated_at = NOW() WHERE id = %s",
            (membership_id,),
        )
        return freeze

    @staticmethod
    def unfreeze(membership_id: int) -> dict:
        membership = MembershipService.get_membership(membership_id)
        if not membership:
            raise ValueError('Абонемент не найден')
        if membership.get('status') != 'frozen':
            raise ValueError('Абонемент не заморожен')
        freeze = MembershipService.active_freeze(membership_id)
        if not freeze:
            raise ValueError('Нет активной записи заморозки')

        today = date.today()
        starts = freeze['starts_on']
        if isinstance(starts, datetime):
            starts = starts.date()
        days = max(1, (today - starts).days)
        max_days = SettingsService.get_int('freeze_max_days_per_year', 30)
        # Cap extension so yearly budget is respected relative to already closed freezes
        closed = fetch_one(
            """
            SELECT COALESCE(SUM(days_used), 0)::int AS days
            FROM membership_freezes
            WHERE membership_id = %s
              AND ends_on IS NOT NULL
              AND EXTRACT(YEAR FROM starts_on) = %s
            """,
            (membership_id, today.year),
        )
        closed_days = int(closed['days']) if closed else 0
        remaining_budget = max(0, max_days - closed_days)
        days = min(days, remaining_budget) if remaining_budget else days

        execute(
            """
            UPDATE membership_freezes
            SET ends_on = %s, days_used = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (today, days, freeze['id']),
        )
        execute(
            """
            UPDATE memberships
            SET status = 'active',
                ends_on = ends_on + (%s * INTERVAL '1 day'),
                updated_at = NOW()
            WHERE id = %s
            """,
            (days, membership_id),
        )
        updated = MembershipService.get_membership(membership_id)
        updated['freeze_days_added'] = days
        return updated

    @staticmethod
    def list_freezes(membership_id: int) -> list[dict]:
        return fetch_all(
            """
            SELECT * FROM membership_freezes
            WHERE membership_id = %s
            ORDER BY starts_on DESC, id DESC
            """,
            (membership_id,),
        )

    @staticmethod
    def sell(member_id: int, plan_id: int, method: str, created_by: int | None, note: str = '') -> dict:
        plan = fetch_one('SELECT * FROM membership_plans WHERE id = %s', (plan_id,))
        if not plan:
            raise ValueError('План не найден')
        starts = date.today()
        ends = starts + timedelta(days=int(plan['duration_days']))
        membership = execute_returning(
            """
            INSERT INTO memberships (member_id, plan_id, starts_on, ends_on, visits_remaining, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                member_id,
                plan_id,
                starts,
                ends,
                plan.get('visit_limit'),
                'active',
            ),
        )
        from app.services.ops_service import CashService

        method = CashService.normalize_method(method)
        payment = execute_returning(
            """
            INSERT INTO payments (member_id, membership_id, amount_cents, method, note, created_by, cash_shift_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                member_id,
                membership['id'],
                plan['price_cents'],
                method,
                note,
                created_by,
                CashService.open_shift_id(),
            ),
        )
        CashService.record_from_payment(payment, 'Абонемент', created_by)
        membership['payment'] = payment
        membership['computed_status'] = MembershipService.compute_status(
            membership['ends_on'], membership.get('visits_remaining'), membership.get('status')
        )
        return membership

    @staticmethod
    def list_payments(member_id: int | None = None, since: date | None = None) -> list[dict]:
        sql = """
            SELECT p.*, m.full_name, m.card_number
            FROM payments p
            JOIN members m ON m.id = p.member_id
            WHERE 1=1
        """
        params: list = []
        if member_id:
            sql += ' AND p.member_id = %s'
            params.append(member_id)
        if since:
            sql += ' AND p.paid_at >= %s'
            params.append(since)
        sql += ' ORDER BY p.paid_at DESC LIMIT 200'
        return fetch_all(sql, params)

    @staticmethod
    def expiring_members(days: int | None = None) -> list[dict]:
        d = days if days is not None else _expiring_days()
        today = date.today()
        until = today + timedelta(days=d)
        return fetch_all(
            """
            SELECT DISTINCT ON (mb.id)
                mb.*, ms.id AS membership_id, ms.ends_on, ms.visits_remaining, ms.status AS membership_status,
                p.name AS plan_name
            FROM members mb
            JOIN memberships ms ON ms.member_id = mb.id
            LEFT JOIN membership_plans p ON p.id = ms.plan_id
            WHERE ms.ends_on BETWEEN %s AND %s
              AND ms.status <> 'frozen'
              AND (ms.visits_remaining IS NULL OR ms.visits_remaining > 0)
            ORDER BY mb.id, ms.ends_on ASC
            """,
            (today, until),
        )

    @staticmethod
    def expiring_count_on(as_of) -> int:
        d = _expiring_days()
        until = as_of + timedelta(days=d)
        row = fetch_one(
            """
            SELECT COUNT(DISTINCT mb.id)::int AS n
            FROM members mb
            JOIN memberships ms ON ms.member_id = mb.id
            WHERE ms.ends_on BETWEEN %s AND %s
              AND ms.status <> 'frozen'
              AND (ms.visits_remaining IS NULL OR ms.visits_remaining > 0)
            """,
            (as_of, until),
        )
        return int(row['n']) if row else 0

