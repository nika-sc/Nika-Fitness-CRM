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
    def current_shift() -> dict | None:
        return fetch_one("SELECT * FROM cash_shifts WHERE status = 'open' ORDER BY id DESC LIMIT 1")

    @staticmethod
    def open_shift_id() -> int | None:
        row = CashService.current_shift()
        return int(row['id']) if row else None

    PAY_METHODS = ('cash', 'card', 'qr')

    @staticmethod
    def normalize_method(method: str | None) -> str:
        m = (method or 'cash').strip().lower()
        if m == 'transfer':
            return 'card'
        if m not in CashService.PAY_METHODS:
            return 'cash'
        return m

    @staticmethod
    def list_categories(kind: str | None = None) -> list[dict]:
        if kind:
            return fetch_all(
                'SELECT * FROM cash_categories WHERE is_active = TRUE AND kind = %s ORDER BY id',
                (kind,),
            )
        return fetch_all('SELECT * FROM cash_categories WHERE is_active = TRUE ORDER BY kind, id')

    @staticmethod
    def category_id(name: str, kind: str = 'income') -> int | None:
        row = fetch_one(
            'SELECT id FROM cash_categories WHERE name = %s AND kind = %s LIMIT 1',
            (name, kind),
        )
        return int(row['id']) if row else None

    @staticmethod
    def record_tx(
        *,
        amount_cents: int,
        kind: str,
        method: str,
        category_id: int | None,
        member_id: int | None = None,
        payment_id: int | None = None,
        note: str = '',
        created_by: int | None = None,
    ) -> dict | None:
        cents = int(amount_cents or 0)
        if cents <= 0:
            return None
        if kind not in ('income', 'expense'):
            raise ValueError('Некорректный тип операции')
        return execute_returning(
            """
            INSERT INTO cash_transactions
                (amount_cents, kind, method, category_id, member_id, payment_id,
                 cash_shift_id, note, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                cents,
                kind,
                CashService.normalize_method(method),
                category_id,
                member_id,
                payment_id,
                CashService.open_shift_id(),
                (note or '').strip(),
                created_by,
            ),
        )

    @staticmethod
    def record_from_payment(payment: dict, category_name: str, created_by: int | None = None) -> dict | None:
        if not payment or int(payment.get('amount_cents') or 0) <= 0:
            return None
        return CashService.record_tx(
            amount_cents=payment['amount_cents'],
            kind='income',
            method=payment.get('method') or 'cash',
            category_id=CashService.category_id(category_name, 'income'),
            member_id=payment.get('member_id'),
            payment_id=payment.get('id'),
            note=payment.get('note') or '',
            created_by=created_by or payment.get('created_by'),
        )

    @staticmethod
    def summary_for_range(start, end) -> dict:
        row = fetch_one(
            """
            SELECT
              COALESCE(SUM(amount_cents) FILTER (WHERE kind = 'income'), 0)::bigint AS income,
              COALESCE(SUM(amount_cents) FILTER (WHERE kind = 'expense'), 0)::bigint AS expense,
              COALESCE(SUM(amount_cents) FILTER (WHERE kind = 'income' AND method = 'cash'), 0)::bigint AS cash,
              COALESCE(SUM(amount_cents) FILTER (WHERE kind = 'income' AND method = 'card'), 0)::bigint AS card,
              COALESCE(SUM(amount_cents) FILTER (WHERE kind = 'income' AND method = 'qr'), 0)::bigint AS qr
            FROM cash_transactions
            WHERE paid_at::date BETWEEN %s AND %s
            """,
            (start, end),
        )
        income = int(row['income']) if row else 0
        expense = int(row['expense']) if row else 0
        return {
            'income': income,
            'expense': expense,
            'net': income - expense,
            'cash': int(row['cash']) if row else 0,
            'card': int(row['card']) if row else 0,
            'qr': int(row['qr']) if row else 0,
        }

    @staticmethod
    def day_summary(day=None) -> dict:
        from datetime import date as date_cls

        d = day or date_cls.today()
        return CashService.summary_for_range(d, d)

    @staticmethod
    def list_transactions(day=None, limit: int = 200, start=None, end=None) -> list[dict]:
        from datetime import date as date_cls

        if start is None and end is None:
            d = day or date_cls.today()
            start = end = d
        elif start is None:
            start = end
        elif end is None:
            end = start
        return fetch_all(
            """
            SELECT t.*, c.name AS category_name, m.full_name
            FROM cash_transactions t
            LEFT JOIN cash_categories c ON c.id = t.category_id
            LEFT JOIN members m ON m.id = t.member_id
            WHERE t.paid_at::date BETWEEN %s AND %s
            ORDER BY t.id DESC
            LIMIT %s
            """,
            (start, end, limit),
        )

    @staticmethod
    def payment_totals(shift_id: int | None = None, today: bool = False) -> dict:
        sql = """
            SELECT
              COALESCE(SUM(amount_cents), 0)::bigint AS total,
              COALESCE(SUM(amount_cents) FILTER (WHERE method = 'cash'), 0)::bigint AS cash,
              COALESCE(SUM(amount_cents) FILTER (WHERE method IN ('card', 'transfer')), 0)::bigint AS card,
              COALESCE(SUM(amount_cents) FILTER (WHERE method = 'qr'), 0)::bigint AS qr,
              COALESCE(SUM(amount_cents) FILTER (WHERE method NOT IN ('cash', 'card', 'transfer', 'qr')), 0)::bigint AS other,
              COUNT(*)::int AS cnt
            FROM payments
            WHERE 1=1
        """
        params: list = []
        if shift_id:
            sql += ' AND cash_shift_id = %s'
            params.append(shift_id)
        if today:
            sql += ' AND paid_at::date = CURRENT_DATE'
        row = fetch_one(sql, params)
        return {
            'total': int(row['total']) if row else 0,
            'cash': int(row['cash']) if row else 0,
            'card': int(row['card']) if row else 0,
            'qr': int(row['qr']) if row else 0,
            'other': int(row['other']) if row else 0,
            'cnt': int(row['cnt']) if row else 0,
        }

    @staticmethod
    def close_shift(user_id: int, closing_cents: int, note: str = '') -> dict:
        row = fetch_one("SELECT * FROM cash_shifts WHERE status = 'open' ORDER BY id DESC LIMIT 1")
        if not row:
            raise ValueError('Нет открытой смены')
        totals = CashService.payment_totals(shift_id=row['id'])
        expected = int(row['opening_cents'] or 0) + totals['cash']
        variance = int(closing_cents) - expected
        extra = f'ожидалось {expected / 100:.0f} ₽, факт {closing_cents / 100:.0f} ₽, расхождение {variance / 100:.0f} ₽'
        merged = (note or '').strip()
        merged = f'{merged}; {extra}' if merged else extra
        execute(
            """
            UPDATE cash_shifts SET status = 'closed', closed_by = %s, closed_at = NOW(),
              closing_cents = %s, note = %s
            WHERE id = %s
            """,
            (user_id, closing_cents, merged, row['id']),
        )
        closed = fetch_one('SELECT * FROM cash_shifts WHERE id = %s', (row['id'],))
        closed['expected_cents'] = expected
        closed['variance_cents'] = variance
        closed['totals'] = totals
        return closed

    @staticmethod
    def list_shifts(limit: int = 50) -> list[dict]:
        return fetch_all(
            """
            SELECT s.*,
              COALESCE((SELECT SUM(p.amount_cents) FROM payments p WHERE p.cash_shift_id = s.id), 0)::bigint AS sales_cents
            FROM cash_shifts s
            ORDER BY s.id DESC
            LIMIT %s
            """,
            (limit,),
        )

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
    def pay_debt(debt_id: int, amount: float, user_id: int | None, method: str = 'cash') -> dict:
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
        method = CashService.normalize_method(method)
        payment = execute_returning(
            """
            INSERT INTO payments (member_id, amount_cents, method, note, created_by, cash_shift_id)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING *
            """,
            (debt['member_id'], pay, method, f'Погашение долга #{debt_id}', user_id, CashService.open_shift_id()),
        )
        CashService.record_from_payment(payment, 'Прочий приход', user_id)
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
