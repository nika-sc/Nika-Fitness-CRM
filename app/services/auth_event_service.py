"""Shared login lockout + audit trail (per tenant DB, works across workers)."""
from __future__ import annotations

import logging

from app.database.connection import execute, fetch_one

logger = logging.getLogger(__name__)


class AuthEventService:
    @staticmethod
    def record(
        event_type: str,
        client_key: str = '',
        username: str = '',
        ip: str = '',
        user_id: int | None = None,
        member_id: int | None = None,
    ) -> None:
        try:
            execute(
                """
                INSERT INTO auth_events (event_type, client_key, username, ip, user_id, member_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    event_type,
                    (client_key or '')[:255],
                    (username or '')[:128],
                    (ip or '')[:64],
                    user_id,
                    member_id,
                ),
            )
        except Exception:
            logger.warning('auth_events insert failed type=%s', event_type, exc_info=True)

    @staticmethod
    def is_locked(client_key: str, fail_type: str, ok_type: str, cfg) -> str | None:
        window = int(cfg.get('LOGIN_LOCKOUT_WINDOW_SEC', 600))
        duration = int(cfg.get('LOGIN_LOCKOUT_DURATION_SEC', 900))
        threshold = int(cfg.get('LOGIN_LOCKOUT_THRESHOLD', 8))
        try:
            row = fetch_one(
                """
                SELECT COUNT(*) AS n,
                       EXTRACT(EPOCH FROM (NOW() - MAX(created_at))) AS age_sec
                FROM auth_events
                WHERE client_key = %s
                  AND event_type = %s
                  AND created_at > NOW() - (%s * INTERVAL '1 second')
                  AND created_at > COALESCE(
                        (
                          SELECT MAX(created_at) FROM auth_events
                          WHERE client_key = %s AND event_type = %s
                        ),
                        TIMESTAMPTZ 'epoch'
                      )
                """,
                (client_key, fail_type, window, client_key, ok_type),
            )
        except Exception:
            logger.warning('auth_events lockout query failed', exc_info=True)
            return None
        if not row:
            return None
        n = int(row.get('n') or 0)
        if n < threshold:
            return None
        age = float(row.get('age_sec') or 0)
        remaining = int(duration - age)
        if remaining <= 0:
            return None
        return f'Слишком много попыток. Повторите через {remaining} сек.'
