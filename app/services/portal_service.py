"""Member portal: password login + staff password issue."""
from __future__ import annotations

import secrets
import string

from flask import session
from werkzeug.security import check_password_hash, generate_password_hash

from app.database.connection import execute_returning, fetch_one
from app.services.member_service import MemberService
from app.services.membership_service import MembershipService
from app.services.message_service import MessageService
from app.services.schedule_service import ScheduleService


class PortalService:
    @staticmethod
    def generate_password(length: int = 10) -> str:
        alphabet = string.ascii_letters + string.digits
        return 'Fit-' + ''.join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def set_password(member_id: int, password: str | None = None, send_email: bool = True) -> str:
        member = MemberService.get(member_id)
        if not member:
            raise ValueError('Клиент не найден')
        plain = (password or '').strip() or PortalService.generate_password()
        if len(plain) < 6:
            raise ValueError('Пароль не короче 6 символов')
        row = execute_returning(
            """
            UPDATE members SET
                portal_password_hash = %s,
                portal_password_plain = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (generate_password_hash(plain), plain, member_id),
        )
        if send_email:
            email = (row.get('email') or '').strip()
            recipient = email or (row.get('phone') or '')
            MessageService.send(
                'email' if email else 'log',
                recipient,
                'portal_password',
                {
                    'member_id': member_id,
                    'full_name': row.get('full_name'),
                    'login_hint': email or row.get('phone') or row.get('card_number'),
                    'password': plain,
                },
            )
        return plain

    @staticmethod
    def find_by_login(login: str) -> dict | None:
        login = (login or '').strip()
        if not login:
            return None
        return fetch_one(
            """
            SELECT * FROM members
            WHERE status = 'active'
              AND (
                phone = %s
                OR lower(email) = lower(%s)
                OR card_number = %s
              )
            ORDER BY id
            LIMIT 1
            """,
            (login, login, login),
        )

    @staticmethod
    def login(login: str, password: str) -> dict:
        member = PortalService.find_by_login(login)
        if not member:
            raise ValueError('Клиент не найден. Проверьте телефон, email или номер карты')
        if not member.get('portal_password_hash'):
            raise ValueError('Пароль ЛК ещё не выдан — обратитесь на ресепшен')
        if not check_password_hash(member['portal_password_hash'], (password or '').strip()):
            raise ValueError('Неверный пароль')
        session['portal_member_id'] = member['id']
        session['portal_login'] = login.strip()
        return member

    @staticmethod
    def current_member() -> dict | None:
        mid = session.get('portal_member_id')
        if not mid:
            return None
        return MemberService.get(int(mid))

    @staticmethod
    def logout() -> None:
        session.pop('portal_member_id', None)
        session.pop('portal_login', None)
        session.pop('portal_phone', None)

    @staticmethod
    def require_member() -> dict:
        member = PortalService.current_member()
        if not member:
            raise ValueError('Войдите в личный кабинет')
        return member

    @staticmethod
    def book(session_id: int, member_id: int | None = None) -> dict:
        member = PortalService.require_member()
        mid = int(member['id'])
        if member_id is not None and int(member_id) != mid:
            raise ValueError('Нельзя записаться от имени другого клиента')
        membership = MembershipService.current_for_checkin(mid)
        if not membership:
            raise ValueError('Нет активного абонемента для записи')
        booking = ScheduleService.book(int(session_id), mid, source='portal')
        if booking.get('already_booked'):
            raise ValueError('Вы уже записаны на это занятие')
        return booking

    @staticmethod
    def cancel(booking_id: int) -> dict:
        member = PortalService.require_member()
        return ScheduleService.cancel_booking(
            int(booking_id),
            member_id=int(member['id']),
            enforce_portal_window=True,
        )
