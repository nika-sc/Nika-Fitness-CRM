"""Reception check-in and membership alerts."""
from __future__ import annotations

from datetime import date

from app.database.connection import execute, execute_returning, fetch_all, fetch_one
from app.services.alert_service import AlertService
from app.services.member_service import MemberService
from app.services.membership_service import MembershipService
from app.services.notification_service import NotificationService


class CheckinService:
    @staticmethod
    def check_in(
        member_id: int,
        created_by: int | None = None,
        source: str = 'reception',
        zone_code: str | None = None,
        branch_id: int | None = None,
    ) -> dict:
        member = MemberService.get(member_id)
        if not member:
            raise ValueError('Клиент не найден')

        from app.services.settings_service import SettingsService
        from app.services.ops_service import ZoneService
        from app.services.growth_service import MedicalService
        from app.services.crm_extra_service import LoyaltyService
        from app.services.feature_flags_service import FeatureFlagsService

        if SettingsService.get_bool('enforce_medical_cert', False):
            if not MedicalService.is_valid(member_id):
                raise ValueError('Нет действующей медсправки')

        zone = zone_code or SettingsService.get('default_access_zone', 'gym')
        if FeatureFlagsService.is_enabled('module_zones'):
            if not ZoneService.member_can_access(member_id, zone):
                raise ValueError(f'Нет доступа в зону «{zone}» по текущему абонементу')

        frozen = MembershipService.current_for_member(member_id)
        if frozen and frozen.get('computed_status') == 'frozen':
            raise ValueError(
                f"Абонемент заморожен до разморозки (карта {member.get('card_number', '')})"
            )

        hours = SettingsService.get_int('gym_presence_hours', 4) or 4
        already = fetch_one(
            """
            SELECT * FROM checkins
            WHERE member_id = %s
              AND checked_out_at IS NULL
              AND checked_at >= NOW() - (%s * INTERVAL '1 hour')
            ORDER BY checked_at DESC
            LIMIT 1
            """,
            (member_id, hours),
        )
        if already:
            membership = MembershipService.current_for_checkin(member_id)
            return {
                'checkin': already,
                'member': member,
                'membership': membership,
                'alert_level': already.get('alert_level') or 'ok',
                'message': 'Уже в зале',
                'already_present': True,
            }

        membership = MembershipService.current_for_checkin(member_id)
        alert_level = 'ok'
        message = 'Абонемент активен'
        severity = 'info'

        if not membership:
            alert_level = 'expired'
            message = 'Нет активного абонемента'
            severity = 'danger'
        else:
            status = membership.get('computed_status') or MembershipService.compute_status(
                membership['ends_on'],
                membership.get('visits_remaining'),
                membership.get('status'),
            )
            if status == 'expired':
                alert_level = 'expired'
                message = f"Абонемент истёк {membership['ends_on']}"
                severity = 'danger'
            elif status == 'expiring':
                alert_level = 'expiring'
                days = (membership['ends_on'] - date.today()).days
                message = f"Абонемент скоро заканчивается ({membership['ends_on']}, ~{days} дн.)"
                severity = 'warning'
            if membership.get('visits_remaining') is not None and membership['visits_remaining'] > 0:
                execute(
                    'UPDATE memberships SET visits_remaining = visits_remaining - 1, updated_at = NOW() WHERE id = %s',
                    (membership['id'],),
                )

        checkin = execute_returning(
            """
            INSERT INTO checkins (member_id, membership_id, source, alert_level, message, created_by, branch_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                member_id,
                membership['id'] if membership else None,
                source,
                alert_level,
                message,
                created_by,
                branch_id,
            ),
        )

        if alert_level == 'ok' and FeatureFlagsService.is_enabled('module_loyalty'):
            try:
                LoyaltyService.award_visit(member_id)
            except Exception:
                pass

        if alert_level in ('expiring', 'expired'):
            AlertService.create(
                alert_type=f'membership_{alert_level}',
                title=f"{member['full_name']} · {member['card_number']}",
                body=message,
                severity=severity,
                member_id=member_id,
                checkin_id=checkin['id'],
            )
            if alert_level == 'expiring' and member.get('email') and membership:
                days_left = (membership['ends_on'] - date.today()).days
                NotificationService.membership_expiring(member, membership, days_left)

        return {
            'checkin': checkin,
            'member': member,
            'membership': membership,
            'alert_level': alert_level,
            'message': message,
        }

    @staticmethod
    def check_in_by_card(
        card_number: str,
        created_by: int | None = None,
        zone_code: str | None = None,
        branch_id: int | None = None,
    ) -> dict:
        member = MemberService.find_by_card(card_number)
        if not member:
            raise ValueError('Карта не найдена')
        return CheckinService.check_in(
            member['id'],
            created_by=created_by,
            source='card',
            zone_code=zone_code,
            branch_id=branch_id,
        )

    @staticmethod
    def recent(limit: int = 30) -> list[dict]:
        return fetch_all(
            """
            SELECT c.*, m.full_name, m.card_number, m.photo_path
            FROM checkins c
            JOIN members m ON m.id = c.member_id
            ORDER BY c.checked_at DESC
            LIMIT %s
            """,
            (limit,),
        )

    @staticmethod
    def today_visits(*, present_only: bool = False) -> list[dict]:
        from app.services.settings_service import SettingsService

        hours = SettingsService.get_int('gym_presence_hours', 4) or 4
        if present_only:
            rows = CheckinService.present_now()
            for row in rows:
                row['in_hall'] = True
            return rows
        return fetch_all(
            """
            SELECT c.*, m.full_name, m.card_number, m.photo_path,
                   (c.checked_out_at IS NULL
                    AND c.checked_at >= NOW() - (%s * INTERVAL '1 hour')) AS in_hall
            FROM checkins c
            JOIN members m ON m.id = c.member_id
            WHERE c.checked_at::date = CURRENT_DATE
            ORDER BY c.checked_at DESC
            """,
            (hours,),
        )

    @staticmethod
    def for_member(member_id: int, limit: int = 50) -> list[dict]:
        return fetch_all(
            """
            SELECT * FROM checkins
            WHERE member_id = %s
            ORDER BY checked_at DESC
            LIMIT %s
            """,
            (member_id, limit),
        )

    @staticmethod
    def today_stats() -> dict:
        row = fetch_one(
            """
            SELECT COUNT(*)::int AS checkins,
                   COUNT(DISTINCT member_id)::int AS unique_members
            FROM checkins
            WHERE checked_at::date = CURRENT_DATE
            """
        )
        return {
            'checkins': int(row['checkins']) if row else 0,
            'unique_members': int(row['unique_members']) if row else 0,
        }

    @staticmethod
    def present_now() -> list[dict]:
        from app.services.settings_service import SettingsService

        hours = SettingsService.get_int('gym_presence_hours', 4) or 4
        return fetch_all(
            """
            SELECT * FROM (
              SELECT DISTINCT ON (c.member_id)
                     c.*, m.full_name, m.card_number, m.photo_path
              FROM checkins c
              JOIN members m ON m.id = c.member_id
              WHERE c.checked_out_at IS NULL
                AND c.checked_at >= NOW() - (%s * INTERVAL '1 hour')
              ORDER BY c.member_id, c.checked_at DESC
            ) present
            ORDER BY checked_at DESC
            """,
            (hours,),
        )

    @staticmethod
    def checkout(checkin_id: int) -> dict:
        current = fetch_one('SELECT * FROM checkins WHERE id = %s', (checkin_id,))
        if not current:
            raise ValueError('Чекин не найден')
        execute(
            """
            UPDATE checkins
            SET checked_out_at = COALESCE(checked_out_at, NOW())
            WHERE member_id = %s AND checked_out_at IS NULL
            """,
            (current['member_id'],),
        )
        return current

    @staticmethod
    def hourly_today() -> list[dict]:
        return fetch_all(
            """
            SELECT EXTRACT(HOUR FROM checked_at)::int AS hour, COUNT(*)::int AS cnt
            FROM checkins
            WHERE checked_at::date = CURRENT_DATE
            GROUP BY 1
            ORDER BY 1
            """
        )

    @staticmethod
    def stats_for_range(start, end) -> dict:
        row = fetch_one(
            """
            SELECT COUNT(*)::int AS checkins,
                   COUNT(DISTINCT member_id)::int AS unique_members
            FROM checkins
            WHERE checked_at::date BETWEEN %s AND %s
            """,
            (start, end),
        )
        return {
            'checkins': int(row['checkins']) if row else 0,
            'unique_members': int(row['unique_members']) if row else 0,
        }

    @staticmethod
    def delta_pair(current: int, previous: int) -> dict:
        diff = int(current) - int(previous)
        return {'value': diff, 'sign': 'up' if diff > 0 else ('down' if diff < 0 else 'flat')}

