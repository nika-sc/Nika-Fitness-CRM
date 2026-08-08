"""Outbound SMS/Telegram/push stubs → message_outbox."""
from __future__ import annotations

import json
import logging

from app.database.connection import execute_returning, fetch_all

logger = logging.getLogger(__name__)


class MessageService:
    @staticmethod
    def send(channel: str, recipient: str, template_key: str, payload: dict | None = None) -> dict:
        body = json.dumps(payload or {}, ensure_ascii=False)
        logger.info('Message stub channel=%s to=%s template=%s', channel, recipient, template_key)
        return execute_returning(
            """
            INSERT INTO message_outbox (channel, recipient, template_key, payload, status)
            VALUES (%s, %s, %s, %s, 'sent')
            RETURNING *
            """,
            (channel, recipient or '', template_key, body),
        )

    @staticmethod
    def list_recent(limit: int = 100) -> list[dict]:
        return fetch_all(
            'SELECT * FROM message_outbox ORDER BY created_at DESC LIMIT %s',
            (limit,),
        )
