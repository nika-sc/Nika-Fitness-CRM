"""Branches, online payments stub, medical, SPA/bar/kids, kiosk, push."""
from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime

from app.database.connection import execute, execute_returning, fetch_all, fetch_one
from app.services.message_service import MessageService


class BranchService:
    @staticmethod
    def list_all(active_only: bool = True) -> list[dict]:
        if active_only:
            return fetch_all('SELECT * FROM branches WHERE is_active ORDER BY name')
        return fetch_all('SELECT * FROM branches ORDER BY name')

    @staticmethod
    def create(code: str, name: str, address: str = '') -> dict:
        return execute_returning(
            'INSERT INTO branches (code, name, address) VALUES (%s, %s, %s) RETURNING *',
            (code.strip().lower(), name.strip(), address or ''),
        )


class PaymentIntentService:
    @staticmethod
    def create(member_id: int | None, amount: float, purpose: str, user_id: int | None) -> dict:
        cents = int(round(float(amount) * 100))
        ext = f'stub_{uuid.uuid4().hex[:16]}'
        return execute_returning(
            """
            INSERT INTO payment_intents (member_id, amount_cents, purpose, status, provider, external_id, created_by)
            VALUES (%s, %s, %s, 'pending', 'stub', %s, %s) RETURNING *
            """,
            (member_id, cents, purpose or 'membership', ext, user_id),
        )

    @staticmethod
    def mark_paid(intent_id: int) -> dict:
        intent = fetch_one('SELECT * FROM payment_intents WHERE id = %s', (intent_id,))
        if not intent:
            raise ValueError('Платёж не найден')
        execute(
            "UPDATE payment_intents SET status = 'paid', paid_at = NOW() WHERE id = %s",
            (intent_id,),
        )
        if intent.get('member_id') and intent['amount_cents'] > 0:
            from app.services.ops_service import CashService

            execute_returning(
                """
                INSERT INTO payments (member_id, amount_cents, method, note, cash_shift_id)
                VALUES (%s, %s, 'online', %s, %s) RETURNING id
                """,
                (
                    intent['member_id'],
                    intent['amount_cents'],
                    f"Online {intent['external_id']}",
                    CashService.open_shift_id(),
                ),
            )
        return fetch_one('SELECT * FROM payment_intents WHERE id = %s', (intent_id,))

    @staticmethod
    def list_recent(limit: int = 100) -> list[dict]:
        return fetch_all(
            """
            SELECT p.*, m.full_name FROM payment_intents p
            LEFT JOIN members m ON m.id = p.member_id
            ORDER BY p.created_at DESC LIMIT %s
            """,
            (limit,),
        )


class MedicalService:
    @staticmethod
    def latest(member_id: int) -> dict | None:
        return fetch_one(
            'SELECT * FROM medical_certificates WHERE member_id = %s ORDER BY expires_on DESC LIMIT 1',
            (member_id,),
        )

    @staticmethod
    def add(member_id: int, expires_on: str, issued_on: str | None = None, note: str = '') -> dict:
        return execute_returning(
            """
            INSERT INTO medical_certificates (member_id, issued_on, expires_on, note)
            VALUES (%s, %s, %s, %s) RETURNING *
            """,
            (member_id, issued_on or None, expires_on, note or ''),
        )

    @staticmethod
    def is_valid(member_id: int) -> bool:
        cert = MedicalService.latest(member_id)
        if not cert:
            return False
        exp = cert['expires_on']
        if isinstance(exp, datetime):
            exp = exp.date()
        return exp >= date.today()


class SpaService:
    @staticmethod
    def list_services(category: str | None = None) -> list[dict]:
        if category:
            return fetch_all(
                'SELECT * FROM spa_services WHERE is_active AND category = %s ORDER BY name',
                (category,),
            )
        return fetch_all('SELECT * FROM spa_services WHERE is_active ORDER BY category, name')

    @staticmethod
    def book(service_id: int, member_id: int | None, starts_at: str) -> dict:
        starts = datetime.fromisoformat(starts_at)
        return execute_returning(
            """
            INSERT INTO spa_bookings (service_id, member_id, starts_at)
            VALUES (%s, %s, %s) RETURNING *
            """,
            (service_id, member_id, starts),
        )

    @staticmethod
    def list_bookings(limit: int = 100) -> list[dict]:
        return fetch_all(
            """
            SELECT b.*, s.name AS service_name, m.full_name
            FROM spa_bookings b
            JOIN spa_services s ON s.id = b.service_id
            LEFT JOIN members m ON m.id = b.member_id
            ORDER BY b.starts_at DESC LIMIT %s
            """,
            (limit,),
        )

    @staticmethod
    def bar_sale(item_name: str, amount: float, member_id: int | None, user_id: int | None) -> dict:
        from app.services.ops_service import CashService

        shift = CashService.current_shift()
        return execute_returning(
            """
            INSERT INTO bar_sales (item_name, amount_cents, member_id, cash_shift_id, created_by)
            VALUES (%s, %s, %s, %s, %s) RETURNING *
            """,
            (
                item_name.strip(),
                int(round(float(amount) * 100)),
                member_id,
                shift['id'] if shift else None,
                user_id,
            ),
        )

    @staticmethod
    def kids_book(parent_id: int, child_name: str, starts_at: str, ends_at: str) -> dict:
        return execute_returning(
            """
            INSERT INTO kids_slots (parent_member_id, child_name, starts_at, ends_at)
            VALUES (%s, %s, %s, %s) RETURNING *
            """,
            (parent_id, child_name.strip(), datetime.fromisoformat(starts_at), datetime.fromisoformat(ends_at)),
        )

    @staticmethod
    def list_kids(limit: int = 50) -> list[dict]:
        return fetch_all(
            """
            SELECT k.*, m.full_name AS parent_name FROM kids_slots k
            JOIN members m ON m.id = k.parent_member_id
            ORDER BY k.starts_at DESC LIMIT %s
            """,
            (limit,),
        )


class KioskService:
    @staticmethod
    def ensure_device(name: str = 'Ресепшен киоск') -> dict:
        row = fetch_one('SELECT * FROM kiosk_devices WHERE is_active ORDER BY id LIMIT 1')
        if row:
            return row
        return execute_returning(
            'INSERT INTO kiosk_devices (name, token) VALUES (%s, %s) RETURNING *',
            (name, secrets.token_hex(16)),
        )

    @staticmethod
    def get_by_token(token: str | None) -> dict | None:
        value = (token or '').strip()
        if len(value) < 16:
            return None
        return fetch_one(
            'SELECT * FROM kiosk_devices WHERE token = %s AND is_active',
            (value,),
        )


class PushService:
    @staticmethod
    def subscribe(member_id: int | None, endpoint: str, keys_json: str = '') -> dict:
        return execute_returning(
            """
            INSERT INTO push_subscriptions (member_id, endpoint, keys_json)
            VALUES (%s, %s, %s) RETURNING *
            """,
            (member_id, endpoint, keys_json or ''),
        )

    @staticmethod
    def notify_member(member_id: int, template_key: str, payload: dict | None = None) -> None:
        subs = fetch_all('SELECT * FROM push_subscriptions WHERE member_id = %s', (member_id,))
        for s in subs:
            MessageService.send('push', s['endpoint'][:120], template_key, payload)
