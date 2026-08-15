"""Aggregated member portal dashboard payload (no SQL in routes/templates)."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from app.database.connection import fetch_all, fetch_one
from app.services.crm_extra_service import LoyaltyService
from app.services.feature_flags_service import FeatureFlagsService
from app.services.growth_service import MedicalService
from app.services.membership_service import MembershipService
from app.services.pt_service import PtService
from app.services.schedule_service import ScheduleService
from app.services.settings_service import SettingsService
from app.services.trainer_slot_service import TrainerSlotService


class MemberPortalService:
    @staticmethod
    def dashboard(member_id: int) -> dict:
        member = fetch_one('SELECT * FROM members WHERE id = %s', (member_id,))
        if not member:
            raise ValueError('Клиент не найден')

        memberships = MembershipService.list_for_member(member_id)
        active = MembershipService.current_for_member(member_id)
        previous = [m for m in memberships if not active or m['id'] != active['id']][:8]

        first_membership_start = None
        if memberships:
            starts = [m['starts_on'] for m in memberships if m.get('starts_on')]
            if starts:
                first_membership_start = min(starts)

        visit_stats = MemberPortalService._visit_stats(member_id)
        weekly = MemberPortalService._weekly_visits(member_id, weeks=12)

        payments = MembershipService.list_payments(member_id=member_id)
        paid_total = sum(int(p.get('amount_cents') or 0) for p in payments)
        last_payment = payments[0] if payments else None
        open_debt = fetch_one(
            """
            SELECT COALESCE(SUM(amount_cents - paid_cents), 0)::bigint AS cents
            FROM debts
            WHERE member_id = %s AND status = 'open'
            """,
            (member_id,),
        )

        upcoming = ScheduleService.list_bookings_for_member(member_id, upcoming_only=True, limit=20)
        history = [
            b
            for b in ScheduleService.list_bookings_for_member(member_id, upcoming_only=False, limit=40)
            if b.get('id') not in {u.get('id') for u in upcoming}
        ][:20]

        sessions = ScheduleService.list_sessions()
        booked_session_ids = {int(b['session_id']) for b in upcoming if b.get('status') == 'booked'}
        cancel_hours = SettingsService.get_int('portal_cancel_before_hours', 2)
        now = datetime.now()
        for b in upcoming:
            starts = b.get('starts_at')
            if isinstance(starts, str):
                starts = datetime.fromisoformat(starts)
            if starts and getattr(starts, 'tzinfo', None):
                now_cmp = datetime.now(starts.tzinfo)
            else:
                now_cmp = now
            b['can_cancel'] = bool(
                starts and (starts - now_cmp) >= timedelta(hours=cancel_hours)
            )

        catalog = []
        for s in sessions:
            sid = int(s['id'])
            booked_count = int(s.get('booked_count') or 0)
            capacity = int(s.get('capacity') or 0)
            is_booked = sid in booked_session_ids
            is_full = booked_count >= capacity
            if is_booked:
                state = 'booked'
            elif is_full:
                state = 'full'
            else:
                state = 'available'
            catalog.append({**s, 'state': state, 'is_booked': is_booked, 'is_full': is_full})

        loyalty = LoyaltyService.get_account(member_id)
        medical = MedicalService.latest(member_id)
        medical_valid = MedicalService.is_valid(member_id) if medical else False
        pt_packages = [
            p for p in PtService.list_packages(member_id) if p.get('status') == 'active' and int(p.get('sessions_left') or 0) > 0
        ]

        slots_enabled = FeatureFlagsService.is_enabled('module_trainer_slots')
        my_slots = TrainerSlotService.list_for_member(member_id) if slots_enabled else []
        open_slots = TrainerSlotService.list_open(days=14) if slots_enabled else []
        for slot in my_slots:
            starts = slot.get('starts_at')
            if isinstance(starts, str):
                starts = datetime.fromisoformat(starts)
            now_cmp = datetime.now(starts.tzinfo) if getattr(starts, 'tzinfo', None) else now
            slot['can_cancel'] = slot.get('status') == 'pending' or bool(
                starts and (starts - now_cmp) >= timedelta(hours=cancel_hours)
            )

        member_since = member.get('created_at')
        if isinstance(member_since, datetime):
            member_since_date = member_since.date()
        elif isinstance(member_since, date):
            member_since_date = member_since
        else:
            member_since_date = None

        return {
            'member': member,
            'member_since': member_since_date,
            'first_membership_start': first_membership_start,
            'active_membership': active,
            'previous_memberships': previous,
            'visits': visit_stats,
            'weekly_visits': weekly,
            'payments': {
                'total_cents': paid_total,
                'last': last_payment,
                'recent': payments[:10],
                'open_debt_cents': int(open_debt['cents']) if open_debt else 0,
            },
            'upcoming_bookings': upcoming,
            'booking_history': history,
            'catalog': catalog,
            'cancel_before_hours': cancel_hours,
            'loyalty': loyalty,
            'medical': medical,
            'medical_valid': medical_valid,
            'pt_packages': pt_packages,
            'trainer_slots_enabled': slots_enabled,
            'my_trainer_slots': my_slots,
            'open_trainer_slots': open_slots,
            'max_active_trainer_slots': SettingsService.get_int('pt_max_active_bookings', 3),
        }

    @staticmethod
    def _visit_stats(member_id: int) -> dict:
        row = fetch_one(
            """
            SELECT
              COUNT(*)::int AS total,
              COUNT(*) FILTER (WHERE checked_at >= NOW() - INTERVAL '30 days')::int AS last_30,
              COUNT(*) FILTER (
                WHERE checked_at >= date_trunc('month', CURRENT_DATE)
                  AND checked_at < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
              )::int AS this_month,
              MIN(checked_at) AS first_visit,
              MAX(checked_at) AS last_visit
            FROM checkins
            WHERE member_id = %s
            """,
            (member_id,),
        )
        total = int(row['total']) if row else 0
        first = row['first_visit'] if row else None
        last = row['last_visit'] if row else None
        avg_month = 0.0
        if first and total:
            start = first.date() if isinstance(first, datetime) else first
            months = max(1, (date.today().year - start.year) * 12 + (date.today().month - start.month) + 1)
            avg_month = round(total / months, 1)
        return {
            'total': total,
            'last_30': int(row['last_30']) if row else 0,
            'this_month': int(row['this_month']) if row else 0,
            'avg_per_month': avg_month,
            'first_visit': first,
            'last_visit': last,
        }

    @staticmethod
    def _weekly_visits(member_id: int, weeks: int = 12) -> list[dict]:
        rows = fetch_all(
            """
            WITH weeks AS (
              SELECT generate_series(
                date_trunc('week', CURRENT_DATE) - ((%s - 1) * INTERVAL '1 week'),
                date_trunc('week', CURRENT_DATE),
                INTERVAL '1 week'
              ) AS week_start
            )
            SELECT w.week_start::date AS week_start,
                   COALESCE(COUNT(c.id), 0)::int AS visits
            FROM weeks w
            LEFT JOIN checkins c
              ON c.member_id = %s
             AND c.checked_at >= w.week_start
             AND c.checked_at < w.week_start + INTERVAL '1 week'
            GROUP BY w.week_start
            ORDER BY w.week_start
            """,
            (weeks, member_id),
        )
        return rows
