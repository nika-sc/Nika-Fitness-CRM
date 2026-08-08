"""App settings key/value helpers."""
from __future__ import annotations

from app.database.connection import execute, fetch_one


class SettingsService:
    @staticmethod
    def get(key: str, default: str = '') -> str:
        row = fetch_one('SELECT value FROM app_settings WHERE key = %s', (key,))
        if not row:
            return default
        return row.get('value') if row.get('value') is not None else default

    @staticmethod
    def get_int(key: str, default: int = 0) -> int:
        raw = SettingsService.get(key, str(default))
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def get_bool(key: str, default: bool = False) -> bool:
        raw = (SettingsService.get(key, 'true' if default else 'false') or '').strip().lower()
        return raw in ('1', 'true', 'yes', 'on')

    @staticmethod
    def set(key: str, value: str) -> None:
        execute(
            """
            INSERT INTO app_settings (key, value) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """,
            (key, value),
        )
