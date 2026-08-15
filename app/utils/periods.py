"""Shared date-period chips for reception stats and cash journal."""
from calendar import monthrange
from datetime import date, timedelta

PERIODS = (
    ('today', 'Сегодня'),
    ('yesterday', 'Вчера'),
    ('day_before', 'Позавчера'),
    ('week', 'Неделя'),
    ('month', 'Месяц'),
    ('quarter', 'Квартал'),
    ('year', 'Год'),
    ('custom', 'Произвольно'),
)


def parse_date(raw: str | None):
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def period_bounds(period: str, date_from: date | None, date_to: date | None) -> tuple[date, date]:
    today = date.today()
    if period == 'custom' and date_from and date_to:
        start, end = date_from, date_to
        if start > end:
            start, end = end, start
        return start, end
    if period == 'yesterday':
        d = today - timedelta(days=1)
        return d, d
    if period == 'day_before':
        d = today - timedelta(days=2)
        return d, d
    if period == 'week':
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)
    if period == 'month':
        start = today.replace(day=1)
        last = monthrange(today.year, today.month)[1]
        return start, today.replace(day=last)
    if period == 'quarter':
        q = (today.month - 1) // 3
        start_month = q * 3 + 1
        start = date(today.year, start_month, 1)
        end_month = start_month + 2
        last = monthrange(today.year, end_month)[1]
        return start, date(today.year, end_month, last)
    if period == 'year':
        return date(today.year, 1, 1), date(today.year, 12, 31)
    return today, today
