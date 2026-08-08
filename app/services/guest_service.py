"""One-off guest visits at reception."""
from __future__ import annotations

from app.database.connection import execute_returning, fetch_all, fetch_one
from app.services.member_service import MemberService


class GuestService:
    @staticmethod
    def list_today(limit: int = 50) -> list[dict]:
        return fetch_all(
            """
            SELECT g.*,
                   h.full_name AS host_name,
                   h.card_number AS host_card
            FROM guest_visits g
            LEFT JOIN members h ON h.id = g.host_member_id
            WHERE g.created_at::date = CURRENT_DATE
            ORDER BY g.created_at DESC
            LIMIT %s
            """,
            (limit,),
        )

    @staticmethod
    def create(
        guest_name: str,
        guest_phone: str = '',
        host_member_id: int | None = None,
        amount: float | int | str | None = 0,
        method: str = 'cash',
        note: str = '',
        created_by: int | None = None,
    ) -> dict:
        name = (guest_name or '').strip()
        if not name:
            raise ValueError('Укажите имя гостя')
        phone = (guest_phone or '').strip()
        host_id = int(host_member_id) if host_member_id else None
        if host_id:
            host = MemberService.get(host_id)
            if not host:
                raise ValueError('Хост-клиент не найден')

        try:
            amount_cents = int(round(float(amount or 0) * 100))
        except (TypeError, ValueError):
            amount_cents = 0
        if amount_cents < 0:
            raise ValueError('Сумма не может быть отрицательной')

        payment_id = None
        if amount_cents > 0 and host_id:
            payment = execute_returning(
                """
                INSERT INTO payments (member_id, membership_id, amount_cents, method, note, created_by)
                VALUES (%s, NULL, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    host_id,
                    amount_cents,
                    method or 'cash',
                    (note or f'Гостевой визит: {name}').strip(),
                    created_by,
                ),
            )
            payment_id = payment['id'] if payment else None

        return execute_returning(
            """
            INSERT INTO guest_visits
                (guest_name, guest_phone, host_member_id, payment_id, amount_cents, note, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                name,
                phone,
                host_id,
                payment_id,
                amount_cents,
                (note or '').strip(),
                created_by,
            ),
        )

    @staticmethod
    def count_today() -> int:
        row = fetch_one(
            "SELECT COUNT(*)::int AS c FROM guest_visits WHERE created_at::date = CURRENT_DATE"
        )
        return int(row['c']) if row else 0
