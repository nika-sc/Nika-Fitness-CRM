"""Members and unique card numbers."""
from __future__ import annotations

import random
import string
from datetime import date

from app.database.connection import execute, execute_returning, fetch_all, fetch_one


class MemberService:
    @staticmethod
    def generate_card_number() -> str:
        for _ in range(20):
            suffix = ''.join(random.choices(string.digits, k=8))
            card = f'NF{date.today().year}{suffix}'
            if not fetch_one('SELECT id FROM members WHERE card_number = %s', (card,)):
                return card
        raise RuntimeError('Unable to generate unique card number')

    @staticmethod
    def list_members(q: str | None = None, limit: int = 100) -> list[dict]:
        if q:
            like = f'%{q.strip()}%'
            return fetch_all(
                """
                SELECT * FROM members
                WHERE full_name ILIKE %s OR phone ILIKE %s OR email ILIKE %s OR card_number ILIKE %s
                ORDER BY full_name
                LIMIT %s
                """,
                (like, like, like, like, limit),
            )
        return fetch_all('SELECT * FROM members ORDER BY full_name LIMIT %s', (limit,))

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
