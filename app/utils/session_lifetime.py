"""Staff session length: until the next local midnight."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask.sessions import SecureCookieSessionInterface


def club_timezone(offset_hours: int | None) -> timezone:
    hours = int(offset_hours if offset_hours is not None else 3)
    return timezone(timedelta(hours=hours))


def next_local_midnight(offset_hours: int | None = 3) -> datetime:
    tz = club_timezone(offset_hours)
    now = datetime.now(tz)
    nxt = datetime.combine(now.date() + timedelta(days=1), datetime.min.time(), tzinfo=tz)
    return nxt


def next_midnight_timestamp(offset_hours: int | None = 3) -> float:
    return next_local_midnight(offset_hours).timestamp()


class MidnightSessionInterface(SecureCookieSessionInterface):
    """Keep a remembered session cookie until staff_until (next midnight)."""

    def get_expiration_time(self, app, session):
        until = session.get('staff_until')
        if until:
            try:
                return datetime.fromtimestamp(float(until), tz=timezone.utc)
            except (TypeError, ValueError):
                pass
        return super().get_expiration_time(app, session)
