"""Defensive helpers: redirects, HMAC, roles, session rotate, image sniff, headers."""
from __future__ import annotations

import hashlib
import hmac
import re
from typing import Iterable

from flask import session
from werkzeug.security import check_password_hash as werkzeug_check_password_hash
from werkzeug.security import generate_password_hash

DEFAULT_SECRET_KEY = 'dev-secret-key-change-in-production'
STAFF_ROLES = frozenset({'reception', 'trainer', 'admin', 'owner'})
GENERIC_LOGIN_ERROR = 'Неверный логин или пароль'

_SAFE_NEXT_RE = re.compile(r'^/[a-zA-Z0-9/_-]*$')


def safe_next_url(nxt: str | None, fallback: str) -> str:
    """Allow only a same-origin relative path (no protocol-relative // or scheme)."""
    if not nxt:
        return fallback
    value = nxt.strip()
    if not value.startswith('/') or value.startswith('//') or '\\' in value or '://' in value:
        return fallback
    if not _SAFE_NEXT_RE.match(value):
        return fallback
    return value


def rotate_session(preserve: Iterable[str] = ()) -> None:
    kept = {key: session[key] for key in preserve if key in session}
    session.clear()
    session.update(kept)


def hmac_sha256_hex(secret: str, body: bytes) -> str:
    return hmac.new((secret or '').encode('utf-8'), body, hashlib.sha256).hexdigest()


def verify_hmac_sha256(secret: str, body: bytes, header: str | None) -> bool:
    if not secret or not header:
        return False
    given = header.strip()
    if given.lower().startswith('sha256='):
        given = given.split('=', 1)[1].strip()
    expected = hmac_sha256_hex(secret, body)
    if len(given) != len(expected):
        return False
    return hmac.compare_digest(expected, given)


def signed_member_token(purpose: str, member_id: int, secret: str) -> str:
    msg = f'{purpose}:{int(member_id)}'.encode('utf-8')
    return hmac.new((secret or '').encode('utf-8'), msg, hashlib.sha256).hexdigest()[:32]


def verify_signed_member_token(purpose: str, member_id: int, secret: str, token: str | None) -> bool:
    if not token or not secret:
        return False
    expected = signed_member_token(purpose, member_id, secret)
    given = token.strip()
    if len(given) != len(expected):
        return False
    return hmac.compare_digest(expected, given)


def normalize_staff_role(role: str | None, actor_role: str | None) -> str:
    value = (role or 'reception').strip().lower()
    if value not in STAFF_ROLES:
        raise ValueError('Недопустимая роль')
    actor = (actor_role or '').strip().lower()
    if value == 'owner' and actor != 'owner':
        raise ValueError('Роль owner может назначить только владелец')
    return value


def hash_password(password: str) -> str:
    """Argon2id via argon2-cffi; Werkzeug pbkdf2 if the package is missing."""
    try:
        from argon2 import PasswordHasher

        return PasswordHasher().hash(password)
    except ImportError:
        return generate_password_hash(password)


def verify_password(hashed: str, password: str) -> bool:
    stored = hashed or ''
    if stored.startswith('$argon2'):
        try:
            from argon2 import PasswordHasher
            from argon2.exceptions import InvalidHash, VerifyMismatchError

            PasswordHasher().verify(stored, password)
            return True
        except (ImportError, VerifyMismatchError, InvalidHash, ValueError, TypeError):
            return False
    return werkzeug_check_password_hash(stored, password)


HTML_SAFE_TAGS = frozenset({
    'p', 'a', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4',
    'code', 'pre', 'strong', 'em', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'div', 'br', 'blockquote', 'span',
})
HTML_SAFE_ATTRS = {
    'a': {'href', 'title', 'target'},
    'code': {'class'},
    'pre': {'class'},
    'div': {'class'},
    'table': {'class'},
    'span': {'class'},
}


def sanitize_html(html: str) -> str:
    import nh3

    return nh3.clean(
        html or '',
        tags=HTML_SAFE_TAGS,
        attributes=HTML_SAFE_ATTRS,
        url_schemes={'http', 'https', 'mailto'},
        link_rel='noopener',
    )


TALISMAN_CSP = {
    'default-src': "'self'",
    'script-src': ["'self'", "'unsafe-inline'"],
    'style-src': ["'self'", "'unsafe-inline'", 'https://fonts.googleapis.com'],
    'font-src': ["'self'", 'https://fonts.gstatic.com', 'data:'],
    'img-src': ["'self'", 'data:', 'blob:', 'https:'],
    'connect-src': "'self'",
    'worker-src': "'self'",
    'frame-src': [
        'https://yandex.ru',
        'https://*.yandex.ru',
        'https://api-maps.yandex.ru',
    ],
    'frame-ancestors': "'self'",
    'base-uri': "'self'",
    'form-action': "'self'",
}


def detect_image_ext(header: bytes) -> str | None:
    if not header or len(header) < 12:
        return None
    if header.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
        return 'webp'
    return None


def security_headers(path: str) -> dict[str, str]:
    """Extras on top of Flask-Talisman (uploads)."""
    if path.startswith('/static/uploads/'):
        return {
            'X-Content-Type-Options': 'nosniff',
            'Content-Disposition': 'inline',
        }
    return {}
