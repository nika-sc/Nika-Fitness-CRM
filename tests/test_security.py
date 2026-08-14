"""Defensive unit tests — helpers only, no exploit payloads against live systems."""
from __future__ import annotations

import pytest

from app.utils.security import (
    DEFAULT_SECRET_KEY,
    detect_image_ext,
    hash_password,
    hmac_sha256_hex,
    normalize_staff_role,
    safe_next_url,
    sanitize_html,
    signed_member_token,
    verify_hmac_sha256,
    verify_password,
    verify_signed_member_token,
)


def test_safe_next_rejects_protocol_relative():
    assert safe_next_url('//evil.example', '/dashboard') == '/dashboard'
    assert safe_next_url('https://evil.example', '/dashboard') == '/dashboard'
    assert safe_next_url('/\\evil', '/dashboard') == '/dashboard'
    assert safe_next_url('/t/nika/members', '/dashboard') == '/t/nika/members'
    assert safe_next_url('/', '/dashboard') == '/'


def test_hmac_webhook_signature():
    secret = 'test-webhook-secret'
    body = b'{"external_id":"x1"}'
    sig = hmac_sha256_hex(secret, body)
    assert verify_hmac_sha256(secret, body, f'sha256={sig}')
    assert not verify_hmac_sha256(secret, body, None)
    assert not verify_hmac_sha256('', body, sig)
    assert not verify_hmac_sha256(secret, body, 'sha256=deadbeef')


def test_nps_member_token():
    token = signed_member_token('nps', 42, 'secret')
    assert verify_signed_member_token('nps', 42, 'secret', token)
    assert not verify_signed_member_token('nps', 41, 'secret', token)
    assert not verify_signed_member_token('nps', 42, 'secret', None)


def test_staff_role_whitelist():
    assert normalize_staff_role('admin', 'admin') == 'admin'
    assert normalize_staff_role('owner', 'owner') == 'owner'
    with pytest.raises(ValueError):
        normalize_staff_role('owner', 'admin')
    with pytest.raises(ValueError):
        normalize_staff_role('superuser', 'owner')


def test_image_magic_bytes():
    jpeg = b'\xff\xd8\xff' + b'\x00' * 13
    png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 8
    webp = b'RIFF' + b'\x00' * 4 + b'WEBP'
    assert detect_image_ext(jpeg) == 'jpg'
    assert detect_image_ext(png) == 'png'
    assert detect_image_ext(webp) == 'webp'
    assert detect_image_ext(b'<html>' + b'\x00' * 20) is None


def test_portal_set_password_does_not_store_plain():
    import inspect
    from app.services.portal_service import PortalService

    src = inspect.getsource(PortalService.set_password)
    assert 'portal_password_plain = NULL' in src
    assert 'generate_password_hash(plain), plain, member_id' not in src


def test_production_rejects_default_secret(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('SECRET_KEY', DEFAULT_SECRET_KEY)
    from app import create_app
    from app.config import ProductionConfig

    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        create_app(ProductionConfig)


def test_hash_password_verifies():
    hashed = hash_password('correct-horse')
    assert hashed.startswith('$argon2') or hashed.startswith(('pbkdf2:', 'scrypt:'))
    assert verify_password(hashed, 'correct-horse')
    assert not verify_password(hashed, 'wrong')


def test_sanitize_html_strips_unsafe_markup():
    out = sanitize_html('<p>Hi</p><script>alert(1)</script><img src=x onerror=x>')
    assert '<script' not in out.lower()
    assert 'onerror' not in out.lower()
    assert 'Hi' in out


def test_talisman_sets_csp():
    from app import create_app
    from app.config import DevelopmentConfig

    app = create_app(DevelopmentConfig)
    app.config['TESTING'] = True
    with app.test_client() as client:
        resp = client.get('/')
        csp = resp.headers.get('Content-Security-Policy', '')
        assert "default-src 'self'" in csp
        assert 'yandex.ru' in csp


def test_redis_limiter_falls_back_when_unreachable(monkeypatch):
    monkeypatch.setenv('RATELIMIT_STORAGE_URI', 'redis://127.0.0.1:1/0')
    from app import create_app
    from app.config import DevelopmentConfig

    app = create_app(DevelopmentConfig)
    assert app.config['RATELIMIT_STORAGE_URI'] == 'memory://'
