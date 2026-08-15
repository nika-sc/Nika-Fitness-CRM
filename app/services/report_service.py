"""MVP reports."""
from __future__ import annotations

from datetime import date, timedelta

from app.database.connection import fetch_all, fetch_one
from app.services.checkin_service import CheckinService
from app.services.membership_service import MembershipService
from app.services.ops_service import CashService
from app.services.schedule_service import ScheduleService


def fetch_all_upcoming_bookings(limit: int = 15) -> list[dict]:
    return fetch_all(
        """
        SELECT b.id, b.status, b.source, b.created_at,
               m.full_name, m.card_number, m.id AS member_id,
               s.id AS session_id, s.starts_at, ct.name AS class_name
        FROM class_bookings b
        JOIN members m ON m.id = b.member_id
        JOIN class_sessions s ON s.id = b.session_id
        JOIN class_types ct ON ct.id = s.class_type_id
        WHERE b.status = 'booked' AND s.starts_at >= NOW()
        ORDER BY s.starts_at
        LIMIT %s
        """,
        (limit,),
    )


class ReportService:
    @staticmethod
    def summary() -> dict:
        active = fetch_one(
            """
            SELECT COUNT(DISTINCT member_id)::int AS c
            FROM memberships
            WHERE ends_on >= CURRENT_DATE
              AND status <> 'frozen'
              AND (visits_remaining IS NULL OR visits_remaining > 0)
            """
        )
        frozen = fetch_one(
            "SELECT COUNT(*)::int AS c FROM memberships WHERE status = 'frozen'"
        )
        members = fetch_one('SELECT COUNT(*)::int AS c FROM members WHERE status = %s', ('active',))
        payments_week = fetch_one(
            """
            SELECT COALESCE(SUM(amount_cents), 0)::bigint AS total, COUNT(*)::int AS cnt
            FROM payments
            WHERE paid_at >= NOW() - INTERVAL '7 days'
            """
        )
        guests_today = fetch_one(
            "SELECT COUNT(*)::int AS c FROM guest_visits WHERE created_at::date = CURRENT_DATE"
        )
        noshows_week = fetch_one(
            """
            SELECT COUNT(*)::int AS c
            FROM class_bookings
            WHERE status = 'no_show'
              AND created_at >= NOW() - INTERVAL '7 days'
            """
        )
        expiring = MembershipService.expiring_members()
        fill = ScheduleService.fill_rates()
        avg_fill = round(sum(s.get('fill_pct', 0) for s in fill) / len(fill), 1) if fill else 0
        booking_stats = ScheduleService.booking_stats(7)
        today_sessions = ScheduleService.today_sessions()
        portal_bookings = ScheduleService.recent_portal_bookings(hours=24, limit=20)
        upcoming_member_bookings = fetch_all_upcoming_bookings()
        attendance = CheckinService.today_stats()
        hourly_raw = {int(r['hour']): int(r['cnt']) for r in CheckinService.hourly_today()}
        hourly = [{'hour': h, 'cnt': hourly_raw.get(h, 0)} for h in range(6, 23)]
        revenue = CashService.payment_totals(today=True)
        cash_today = CashService.day_summary()
        return {
            'active_memberships': active['c'] if active else 0,
            'frozen_memberships': frozen['c'] if frozen else 0,
            'active_members': members['c'] if members else 0,
            'payments_week_cents': payments_week['total'] if payments_week else 0,
            'payments_week_count': payments_week['cnt'] if payments_week else 0,
            'guests_today': guests_today['c'] if guests_today else 0,
            'noshows_week': booking_stats.get('noshow_week') or (noshows_week['c'] if noshows_week else 0),
            'cancelled_week': booking_stats.get('cancelled_week') or 0,
            'portal_bookings_24h': booking_stats.get('portal_24h') or 0,
            'portal_bookings': portal_bookings,
            'today_sessions': today_sessions,
            'upcoming_member_bookings': upcoming_member_bookings,
            'expiring': expiring,
            'fill_sessions': fill,
            'avg_fill_pct': avg_fill,
            'ltv_avg_cents': ReportService.avg_ltv_cents(),
            'churn_30_pct': ReportService.churn_30_pct(),
            'checkins_today': attendance['checkins'],
            'unique_checkins_today': attendance['unique_members'],
            'hourly_checkins': hourly,
            'revenue_today_cents': revenue['total'],
            'cash_net_today': cash_today['net'],
        }

    @staticmethod
    def avg_ltv_cents() -> int:
        row = fetch_one(
            """
            SELECT COALESCE(AVG(total), 0)::bigint AS avg
            FROM (
              SELECT member_id, SUM(amount_cents)::bigint AS total
              FROM payments GROUP BY member_id
            ) t
            """
        )
        return int(row['avg']) if row else 0

    @staticmethod
    def churn_30_pct() -> float:
        """Share of members whose last membership ended in last 30 days and no active now."""
        churned = fetch_one(
            """
            SELECT COUNT(DISTINCT m.id)::int AS c FROM members m
            WHERE EXISTS (
              SELECT 1 FROM memberships ms WHERE ms.member_id = m.id
                AND ms.ends_on BETWEEN CURRENT_DATE - 30 AND CURRENT_DATE - 1
            )
            AND NOT EXISTS (
              SELECT 1 FROM memberships ms2 WHERE ms2.member_id = m.id
                AND ms2.ends_on >= CURRENT_DATE AND ms2.status <> 'frozen'
                AND (ms2.visits_remaining IS NULL OR ms2.visits_remaining > 0)
            )
            """
        )
        total = fetch_one('SELECT COUNT(*)::int AS c FROM members WHERE status = %s', ('active',))
        t = total['c'] if total and total['c'] else 0
        c = churned['c'] if churned else 0
        return round(100.0 * c / t, 1) if t else 0.0

    @staticmethod
    def payments_period(days: int = 30) -> list[dict]:
        since = date.today() - timedelta(days=days)
        return MembershipService.list_payments(since=since)
