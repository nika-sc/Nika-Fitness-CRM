"""Optional club modules — off by default, toggled in settings."""
from __future__ import annotations

from app.services.settings_service import SettingsService

MODULES: tuple[dict[str, str], ...] = (
    {'key': 'module_leads', 'label': 'Лиды', 'hint': 'Воронка до клиента'},
    {'key': 'module_loyalty', 'label': 'Лояльность', 'hint': 'Баллы и NPS'},
    {'key': 'module_pt', 'label': 'PT', 'hint': 'Персональные тренировки с тренером'},
    {'key': 'module_spa', 'label': 'SPA / бар', 'hint': 'Доп. услуги и бар (позже заменим магазином зала)'},
    {'key': 'module_lockers', 'label': 'Шкафчики', 'hint': 'Аренда шкафчиков'},
    {'key': 'module_corporate', 'label': 'Корпоратив', 'hint': 'B2B-контракты'},
    {'key': 'module_payments_online', 'label': 'Онлайн-оплаты', 'hint': 'Эквайринг (пока заглушка)'},
    {'key': 'module_zones', 'label': 'Зоны доступа', 'hint': 'Зоны при чекине (зал / cardio / pool)'},
    {'key': 'module_messaging', 'label': 'Сообщения', 'hint': 'SMS / Telegram outbox'},
    {'key': 'module_branches', 'label': 'Филиалы', 'hint': 'Несколько точек'},
    {
        'key': 'module_trainer_slots',
        'label': 'Слоты тренера',
        'hint': 'Кабинет тренера и запись на персоналку',
        'default': True,
    },
)

MODULE_KEYS = tuple(item['key'] for item in MODULES)
MODULE_DEFAULTS = {item['key']: bool(item.get('default')) for item in MODULES}


class FeatureFlagsService:
    @staticmethod
    def is_enabled(key: str) -> bool:
        if key not in MODULE_KEYS:
            return True
        return SettingsService.get_bool(key, MODULE_DEFAULTS.get(key, False))

    @staticmethod
    def list_for_settings() -> list[dict]:
        return [
            {**item, 'enabled': FeatureFlagsService.is_enabled(item['key'])}
            for item in MODULES
        ]

    @staticmethod
    def save_from_form(form) -> None:
        for key in MODULE_KEYS:
            SettingsService.set(key, 'true' if form.get(key) else 'false')
