"""Access zones, corporate, cash, lockers."""
from __future__ import annotations

from app.database.connection import execute, execute_returning, fetch_all, fetch_one


class ZoneService:
    @staticmethod
    def list_zones(active_only: bool = True) -> list[dict]:
        if active_only:
            return fetch_all('SELECT * FROM access_zones WHERE is_active ORDER BY name')
        return fetch_all('SELECT * FROM access_zones ORDER BY name')

    @staticmethod
    def create(code: str, name: str) -> dict:
        return execute_returning(
            'INSERT INTO access_zones (code, name) VALUES (%s, %s) RETURNING *',
            (code.strip().lower(), name.strip()),
        )

    @staticmethod
    def set_plan_zones(plan_id: int, zone_ids: list[int]) -> None:
        execute('DELETE FROM plan_zone_access WHERE plan_id = %s', (plan_id,))
        for zid in zone_ids:
            execute(
                'INSERT INTO plan_zone_access (plan_id, zone_id) VALUES (%s, %s) ON CONFLICT DO NOTHING',
                (plan_id, int(zid)),
            )

    @staticmethod
    def plan_zones(plan_id: int) -> list[dict]:
        return fetch_all(
            """
            SELECT z.* FROM access_zones z
            JOIN plan_zone_access p ON p.zone_id = z.id
            WHERE p.plan_id = %s
            """,
            (plan_id,),
        )

    @staticmethod
    def member_can_access(member_id: int, zone_code: str) -> bool:
        from app.services.membership_service import MembershipService
        from app.services.settings_service import SettingsService

        zone_code = zone_code or SettingsService.get('default_access_zone', 'gym')
        membership = MembershipService.current_for_checkin(member_id)
        if not membership:
            return True  # чекин сам сообщит об истёкшем абонементе
        zones = ZoneService.plan_zones(membership['plan_id']) if membership.get('plan_id') else []
        if not zones:
            return True  # no restriction configured
        return any(z['code'] == zone_code for z in zones)


class CorporateService:
    @staticmethod
    def list_all() -> list[dict]:
        return fetch_all(
            """
            SELECT c.*,
              (SELECT COUNT(*) FROM members m WHERE m.corporate_id = c.id)::int AS seats_used
            FROM corporate_accounts c ORDER BY c.name
            """
        )

    @staticmethod
    def create(data: dict) -> dict:
        return execute_returning(
            """
            INSERT INTO corporate_accounts (name, contact_phone, contact_email, seats_limit, note)
            VALUES (%s, %s, %s, %s, %s) RETURNING *
            """,
            (
                data['name'].strip(),
                data.get('contact_phone') or '',
                data.get('contact_email') or '',
                int(data.get('seats_limit') or 10),
                data.get('note') or '',
            ),
        )

    @staticmethod
    def assign_member(member_id: int, corporate_id: int | None) -> None:
        if corporate_id:
            corp = fetch_one(
                """
                SELECT c.*, (SELECT COUNT(*) FROM members m WHERE m.corporate_id = c.id)::int AS used
                FROM corporate_accounts c WHERE c.id = %s
                """,
                (corporate_id,),
            )
            if not corp:
                raise ValueError('Контракт не найден')
            if corp['used'] >= corp['seats_limit']:
                raise ValueError('Лимит мест по контракту исчерпан')
        execute('UPDATE members SET corporate_id = %s, updated_at = NOW() WHERE id = %s', (corporate_id, member_id))


class CashService:
    @staticmethod
    def open_shift(user_id: int, opening_cents: int = 0, note: str = '') -> dict:
        open_one = fetch_one("SELECT id FROM cash_shifts WHERE status = 'open' LIMIT 1")
        if open_one:
            raise ValueError('Уже есть открытая смена')
        return execute_returning(
            """
            INSERT INTO cash_shifts (opened_by, opening_cents, note, status)
            VALUES (%s, %s, %s, 'open') RETURNING *
            """,
            (user_id, opening_cents, note or ''),
        )

    @staticmethod
    def close_shift(user_id: int, closing_cents: int, note: str = '') -> dict:
        row = fetch_one("SELECT * FROM cash_shifts WHERE status = 'open' ORDER BY id DESC LIMIT 1")
        if not row:
            raise ValueError('Нет открытой смены')
        execute(
            """
            UPDATE cash_shifts SET status = 'closed', closed_by = %s, closed_at = NOW(),
              closing_cents = %s, note = CASE WHEN %s = '' THEN note ELSE %s END
            WHERE id = %s
            """,
            (user_id, closing_cents, note or '', note or '', row['id']),
        )
        return fetch_one('SELECT * FROM cash_shifts WHERE id = %s', (row['id'],))

    @staticmethod
    def current_shift() -> dict | None:
        return fetch_one("SELECT * FROM cash_shifts WHERE status = 'open' ORDER BY id DESC LIMIT 1")

    @staticmethod
    def list_shifts(limit: int = 50) -> list[dict]:
        return fetch_all('SELECT * FROM cash_shifts ORDER BY id DESC LIMIT %s', (limit,))

    @staticmethod
    def create_debt(member_id: int, amount: float, note: str, user_id: int | None) -> dict:
        cents = int(round(float(amount) * 100))
        return execute_returning(
            """
            INSERT INTO debts (member_id, amount_cents, note, created_by)
            VALUES (%s, %s, %s, %s) RETURNING *
            """,
            (member_id, cents, note or '', user_id),
        )

    @staticmethod
    def list_debts(status: str = 'open') -> list[dict]:
        return fetch_all(
            """
            SELECT d.*, m.full_name, m.card_number FROM debts d
            JOIN members m ON m.id = d.member_id
            WHERE d.status = %s ORDER BY d.id DESC
            """,
            (status,),
        )

    @staticmethod
    def pay_debt(debt_id: int, amount: float, user_id: int | None) -> dict:
        debt = fetch_one('SELECT * FROM debts WHERE id = %s', (debt_id,))
        if not debt or debt['status'] != 'open':
            raise ValueError('Долг не найден')
        pay = int(round(float(amount) * 100))
        paid = debt['paid_cents'] + pay
        status = 'paid' if paid >= debt['amount_cents'] else 'open'
        execute(
            'UPDATE debts SET paid_cents = %s, status = %s, updated_at = NOW() WHERE id = %s',
            (paid, status, debt_id),
        )
        execute_returning(
            """
            INSERT INTO payments (member_id, amount_cents, method, note, created_by)
            VALUES (%s, %s, 'cash', %s, %s) RETURNING id
            """,
            (debt['member_id'], pay, f'Погашение долга #{debt_id}', user_id),
        )
        return fetch_one('SELECT * FROM debts WHERE id = %s', (debt_id,))


class LockerService:
    @staticmethod
    def list_all() -> list[dict]:
        return fetch_all(
            """
            SELECT l.*, m.full_name FROM lockers l
            LEFT JOIN members m ON m.id = l.member_id
            ORDER BY l.code
            """
        )

    @staticmethod
    def create(code: str, zone: str = 'main') -> dict:
        return execute_returning(
            'INSERT INTO lockers (code, zone) VALUES (%s, %s) RETURNING *',
            (code.strip(), zone or 'main'),
        )

    @staticmethod
    def assign(locker_id: int, member_id: int) -> dict:
        locker = fetch_one('SELECT * FROM lockers WHERE id = %s', (locker_id,))
        if not locker:
            raise ValueError('Шкафчик не найден')
        if locker['status'] != 'free':
            raise ValueError('Шкафчик занят')
        execute(
            "UPDATE lockers SET status = 'busy', member_id = %s, assigned_at = NOW() WHERE id = %s",
            (member_id, locker_id),
        )
        return fetch_one('SELECT * FROM lockers WHERE id = %s', (locker_id,))

    @staticmethod
    def release(locker_id: int) -> dict:
        execute(
            "UPDATE lockers SET status = 'free', member_id = NULL, assigned_at = NULL WHERE id = %s",
            (locker_id,),
        )
        return fetch_one('SELECT * FROM lockers WHERE id = %s', (locker_id,))
