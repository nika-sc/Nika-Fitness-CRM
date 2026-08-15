"""Russian labels for staff CRM (roles, statuses, sources)."""

ROLE_LABELS = {
    'reception': 'Ресепшен',
    'trainer': 'Тренер',
    'admin': 'Админ',
    'owner': 'Владелец',
}

STATUS_LABELS = {
    'active': 'Активен',
    'inactive': 'Неактивен',
    'expiring': 'Истекает',
    'frozen': 'Заморозка',
    'expired': 'Истёк',
    'open': 'Открыта',
    'closed': 'Закрыта',
    'booked': 'Записан',
    'pending': 'Ждёт подтверждения',
    'attended': 'Был',
    'done': 'Проведено',
    'no_show': 'Неявка',
    'cancelled': 'Отмена',
}

METHOD_LABELS = {
    'cash': 'Наличные',
    'card': 'Карта',
    'qr': 'QR',
    'transfer': 'Перевод',
    'online': 'Онлайн',
}

SOURCE_LABELS = {
    'staff': 'Стойка',
    'reception': 'Ресепшен',
    'portal': 'ЛК',
    'kiosk': 'Киоск',
    'trainer': 'Тренер',
}


def _lookup(mapping: dict[str, str], value, fallback: str | None = None) -> str:
    if value is None or value == '':
        return fallback or '—'
    key = str(value)
    return mapping.get(key, fallback if fallback is not None else key)


def role_label(value) -> str:
    return _lookup(ROLE_LABELS, value)


def status_label(value) -> str:
    return _lookup(STATUS_LABELS, value)


def method_label(value) -> str:
    return _lookup(METHOD_LABELS, value)


def source_label(value) -> str:
    return _lookup(SOURCE_LABELS, value)


def status_pill_class(value) -> str:
    key = str(value or '')
    if key in ('active', 'attended', 'done', 'ok', 'open'):
        return 'ok'
    if key in ('expiring', 'frozen', 'booked', 'pending', 'inactive'):
        return 'warn'
    if key in ('expired', 'no_show', 'cancelled', 'closed'):
        return 'danger'
    return ''
