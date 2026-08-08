"""Staff users and RBAC."""
from __future__ import annotations

import time
from collections import defaultdict

from werkzeug.security import check_password_hash, generate_password_hash

from app.database.connection import execute, execute_returning, fetch_all, fetch_one

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
    def create_user(username: str, password: str, full_name: str, role: str) -> dict:
        return execute_returning(
            """
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES (%s, %s, %s, %s)
            RETURNING id, username, full_name, role, is_active
            """,
            (username, generate_password_hash(password), full_name, role),
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
    def authenticate(username: str, password: str, client_key: str, cfg) -> tuple[dict | None, str | None]:
        now = time.time()
        until = _lockouts.get(client_key)
        if until and until > now:
            return None, f'Слишком много попыток. Повторите через {int(until - now)} сек.'

        user = UserService.get_user_by_username(username)
        ok = bool(user and user.get('is_active') and check_password_hash(user['password_hash'], password))
        window = int(cfg.get('LOGIN_LOCKOUT_WINDOW_SEC', 600))
        _login_attempts[client_key] = [t for t in _login_attempts[client_key] if now - t < window]
        if not ok:
            _login_attempts[client_key].append(now)
            if len(_login_attempts[client_key]) >= int(cfg.get('LOGIN_LOCKOUT_THRESHOLD', 8)):
                _lockouts[client_key] = now + int(cfg.get('LOGIN_LOCKOUT_DURATION_SEC', 900))
                _login_attempts[client_key].clear()
            return None, 'Неверный логин или пароль'
        _login_attempts.pop(client_key, None)
        _lockouts.pop(client_key, None)
        return user, None
