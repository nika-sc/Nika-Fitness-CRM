"""Members and unique card numbers."""
from __future__ import annotations

import re

from app.database.connection import execute, execute_returning, fetch_all, fetch_one

VIP_RESERVED = frozenset({
    '111', '123', '222', '333', '444', '555', '666', '777', '888', '999',
    '5555', '7777',
})
SEQ_START = 1000


class MemberService:
    @staticmethod
    def generate_card_number() -> str:
        row = fetch_one(
            """
            SELECT COALESCE(MAX(card_number::bigint), %s - 1) AS n
            FROM members
            WHERE card_number ~ '^[0-9]+$'
              AND length(card_number) <= 12
              AND card_number::bigint >= %s
            """,
            (SEQ_START, SEQ_START),
        )
        n = int(row['n'] if row and row.get('n') is not None else SEQ_START - 1) + 1
        while True:
            card = str(n)
            if card not in VIP_RESERVED and not fetch_one(
                'SELECT id FROM members WHERE card_number = %s', (card,)
            ):
                return card
            n += 1

    @staticmethod
    def available_vip_numbers(current: str | None = None) -> list[str]:
        cards = tuple(VIP_RESERVED)
        placeholders = ','.join(['%s'] * len(cards))
        taken = {
            row['card_number']
            for row in fetch_all(
                f'SELECT card_number FROM members WHERE card_number IN ({placeholders})',
                cards,
            )
        }
        out = [n for n in sorted(VIP_RESERVED, key=lambda x: (len(x), x)) if n not in taken]
        if current and current in VIP_RESERVED and current not in out:
            out.insert(0, current)
        return out

    @staticmethod
    def validate_vip_number(number: str, member_id: int | None = None) -> str:
        card = (number or '').strip()
        if card not in VIP_RESERVED:
            raise ValueError('Этот номер не из резерва VIP')
        existing = fetch_one('SELECT id FROM members WHERE card_number = %s', (card,))
        if existing and existing['id'] != member_id:
            raise ValueError(f'Номер {card} уже занят')
        return card

    @staticmethod
    def _search_clause(q: str | None) -> tuple[str, tuple]:
        if not q or not q.strip():
            return '', ()
        raw = q.strip()
        like = f'%{raw}%'
        digits = re.sub(r'\D+', '', raw)
        if digits:
            digit_like = f'%{digits}%'
            return (
                """ WHERE full_name ILIKE %s
                    OR card_number ILIKE %s
                    OR regexp_replace(phone, '\\D', '', 'g') LIKE %s""",
                (like, like, digit_like),
            )
        return (
            ' WHERE full_name ILIKE %s OR phone ILIKE %s OR email ILIKE %s OR card_number ILIKE %s',
            (like, like, like, like),
        )

    @staticmethod
    def search_public(q: str, limit: int = 15) -> list[dict]:
        raw = (q or '').strip()
        digits = re.sub(r'\D+', '', raw)
        if len(raw) < 3:
            exact = MemberService.find_by_card(raw) if raw else None
            if not exact and digits:
                exact = MemberService.find_by_card(digits)
            if not exact:
                return []
            rows = [exact]
        else:
            rows = MemberService.list_members(q=raw, limit=limit)
            if digits and digits != raw:
                extra = MemberService.find_by_card(digits)
                if extra and extra['id'] not in {r['id'] for r in rows}:
                    rows = [extra] + rows
        out = []
        for row in rows[:limit]:
            out.append({
                'id': row['id'],
                'full_name': row.get('full_name') or '',
                'phone': row.get('phone') or '',
                'card_number': row.get('card_number') or '',
                'photo_path': row.get('photo_path'),
            })
        return out

    @staticmethod
    def count_members(q: str | None = None) -> int:
        where, params = MemberService._search_clause(q)
        row = fetch_one(f'SELECT COUNT(*) AS n FROM members{where}', params)
        return int(row['n']) if row else 0

    @staticmethod
    def list_members(q: str | None = None, limit: int = 100, offset: int = 0) -> list[dict]:
        where, params = MemberService._search_clause(q)
        sql = f'SELECT * FROM members{where} ORDER BY full_name LIMIT %s OFFSET %s'
        return fetch_all(sql, params + (limit, offset))

    @staticmethod
    def attach_membership_summaries(members: list[dict]) -> list[dict]:
        if not members:
            return members
        from app.services.membership_service import MembershipService

        ids = [m['id'] for m in members]
        placeholders = ','.join(['%s'] * len(ids))
        rows = fetch_all(
            f"""
            SELECT DISTINCT ON (ms.member_id)
                ms.member_id, ms.ends_on, ms.visits_remaining, ms.status, p.name AS plan_name
            FROM memberships ms
            LEFT JOIN membership_plans p ON p.id = ms.plan_id
            WHERE ms.member_id IN ({placeholders})
            ORDER BY ms.member_id, ms.ends_on DESC, ms.id DESC
            """,
            tuple(ids),
        )
        by_id = {row['member_id']: row for row in rows}
        for member in members:
            ms = by_id.get(member['id'])
            if not ms:
                member['membership_computed'] = None
                member['membership_ends_on'] = None
                member['membership_plan'] = None
                continue
            member['membership_computed'] = MembershipService.compute_status(
                ms['ends_on'], ms.get('visits_remaining'), ms.get('status')
            )
            member['membership_ends_on'] = ms['ends_on']
            member['membership_plan'] = ms.get('plan_name')
        return members

    @staticmethod
    def get(member_id: int) -> dict | None:
        return fetch_one('SELECT * FROM members WHERE id = %s', (member_id,))

    @staticmethod
    def find_by_card(card_number: str) -> dict | None:
        return fetch_one('SELECT * FROM members WHERE card_number = %s', (card_number.strip(),))

    @staticmethod
    def create(data: dict) -> dict:
        card = data.get('card_number') or MemberService.generate_card_number()
        return execute_returning(
            """
            INSERT INTO members (card_number, full_name, phone, email, photo_path, notes, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                card,
                data['full_name'].strip(),
                (data.get('phone') or '').strip(),
                (data.get('email') or '').strip(),
                data.get('photo_path'),
                (data.get('notes') or '').strip(),
                data.get('status') or 'active',
            ),
        )

    @staticmethod
    def update(member_id: int, data: dict) -> dict | None:
        card = data.get('card_number')
        if card:
            return execute_returning(
                """
                UPDATE members SET
                    full_name = %s,
                    phone = %s,
                    email = %s,
                    photo_path = COALESCE(%s, photo_path),
                    notes = %s,
                    status = %s,
                    card_number = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING *
                """,
                (
                    data['full_name'].strip(),
                    (data.get('phone') or '').strip(),
                    (data.get('email') or '').strip(),
                    data.get('photo_path'),
                    (data.get('notes') or '').strip(),
                    data.get('status') or 'active',
                    card,
                    member_id,
                ),
            )
        return execute_returning(
            """
            UPDATE members SET
                full_name = %s,
                phone = %s,
                email = %s,
                photo_path = COALESCE(%s, photo_path),
                notes = %s,
                status = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (
                data['full_name'].strip(),
                (data.get('phone') or '').strip(),
                (data.get('email') or '').strip(),
                data.get('photo_path'),
                (data.get('notes') or '').strip(),
                data.get('status') or 'active',
                member_id,
            ),
        )

    @staticmethod
    def delete(member_id: int) -> int:
        return execute('DELETE FROM members WHERE id = %s', (member_id,))
