"""Staff users and RBAC."""
from __future__ import annotations

import time
from collections import defaultdict

from app.database.connection import execute_returning, fetch_all, fetch_one
from app.services.auth_event_service import AuthEventService
from app.utils.security import GENERIC_LOGIN_ERROR, hash_password, normalize_staff_role, verify_password

_login_attempts: dict[str, list[float]] = defaultdict(list)
_lockouts: dict[str, float] = {}


class UserService:
    @staticmethod
    def get_user_by_id(user_id: int) -> dict | None:
        return fetch_one(
            'SELECT id, username, password_hash, full_name, role, is_active FROM users WHERE id = %s',
            (user_id,),
        )

    @staticmethod
    def get_user_by_username(username: str) -> dict | None:
        return fetch_one(
            'SELECT id, username, password_hash, full_name, role, is_active FROM users WHERE username = %s',
            (username,),
        )

    @staticmethod
    def list_users() -> list[dict]:
        return fetch_all(
            'SELECT id, username, full_name, role, is_active, created_at FROM users ORDER BY id'
        )

    @staticmethod
    def create_user(
        username: str,
        password: str,
        full_name: str,
        role: str,
        actor_role: str | None = None,
    ) -> dict:
        role = normalize_staff_role(role, actor_role)
        if not (username or '').strip():
            raise ValueError('Укажите логин')
        if len(password or '') < 6:
            raise ValueError('Пароль не короче 6 символов')
        return execute_returning(
            """
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES (%s, %s, %s, %s)
            RETURNING id, username, full_name, role, is_active
            """,
            (username.strip(), hash_password(password), full_name, role),
        )

    @staticmethod
    def check_permission(user_id: int, permission: str) -> bool:
        user = UserService.get_user_by_id(user_id)
        if not user or not user.get('is_active'):
            return False
        if user['role'] in ('admin', 'owner'):
            return True
        row = fetch_one(
            """
            SELECT 1 AS ok
            FROM role_permissions rp
            JOIN permissions p ON p.id = rp.permission_id
            WHERE rp.role = %s AND p.name = %s
            """,
            (user['role'], permission),
        )
        return bool(row)

    @staticmethod
    def authenticate(
        username: str,
        password: str,
        client_key: str,
        cfg,
        ip: str = '',
    ) -> tuple[dict | None, str | None]:
        now = time.time()
        db_lock = AuthEventService.is_locked(client_key, 'login_fail', 'login_ok', cfg)
        if db_lock:
            return None, db_lock
        until = _lockouts.get(client_key)
        if until and until > now:
            return None, f'Слишком много попыток. Повторите через {int(until - now)} сек.'

        user = UserService.get_user_by_username(username)
        ok = bool(user and user.get('is_active') and verify_password(user['password_hash'], password))
        window = int(cfg.get('LOGIN_LOCKOUT_WINDOW_SEC', 600))
        _login_attempts[client_key] = [t for t in _login_attempts[client_key] if now - t < window]
        if not ok:
            _login_attempts[client_key].append(now)
            if len(_login_attempts[client_key]) >= int(cfg.get('LOGIN_LOCKOUT_THRESHOLD', 8)):
                _lockouts[client_key] = now + int(cfg.get('LOGIN_LOCKOUT_DURATION_SEC', 900))
                _login_attempts[client_key].clear()
            AuthEventService.record(
                'login_fail',
                client_key=client_key,
                username=(username or '')[:128],
                ip=ip,
                user_id=(user or {}).get('id'),
            )
            return None, GENERIC_LOGIN_ERROR
        _login_attempts.pop(client_key, None)
        _lockouts.pop(client_key, None)
        AuthEventService.record(
            'login_ok',
            client_key=client_key,
            username=(username or '')[:128],
            ip=ip,
            user_id=user['id'],
        )
        return user, None
