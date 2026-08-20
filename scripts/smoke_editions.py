#!/usr/bin/env python3
"""Smoke-test route maps for selfhosted and saas editions."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
except ImportError:
    pass


def _clear_saas_cache() -> None:
    from app.database import connection
    connection._saas_available.cache_clear()


def _endpoints(app) -> set[str]:
    return {r.endpoint for r in app.url_map.iter_rules() if r.endpoint}


def smoke_selfhosted() -> None:
    os.environ['APP_EDITION'] = 'selfhosted'
    # Keep PLATFORM_DATABASE_URL out of saas_enabled for this process
    saved = os.environ.pop('PLATFORM_DATABASE_URL', None)
    _clear_saas_cache()
    from app import create_app
    app = create_app()
    eps = _endpoints(app)
    assert 'public.index' in eps
    assert 'public.docs' in eps
    assert 'public.health' in eps
    assert 'platform_admin.login' not in eps
    assert 'platform.register' not in eps
    assert not any('/t/<slug>' in str(r) for r in app.url_map.iter_rules())
    print('selfhosted OK', sorted(e for e in eps if e and e.startswith(('public.', 'auth.'))))
    if saved is not None:
        os.environ['PLATFORM_DATABASE_URL'] = saved


def smoke_saas() -> None:
    try:
        import app.saas  # noqa: F401
    except ModuleNotFoundError:
        print('saas package missing — skip saas smoke')
        return
    if not (os.environ.get('PLATFORM_DATABASE_URL') or '').strip():
        print('PLATFORM_DATABASE_URL unset — skip saas smoke')
        return
    os.environ['APP_EDITION'] = 'saas'
    _clear_saas_cache()
    from app import create_app
    app = create_app()
    eps = _endpoints(app)
    assert 'public.index' in eps
    assert 'platform.register' in eps
    assert 'platform.login' in eps
    assert 'platform.demo' in eps
    assert 'platform_admin.login' in eps
    assert any('/t/<slug>' in str(r) for r in app.url_map.iter_rules())
    print('saas OK', sorted(e for e in eps if e and e.startswith(('public.', 'platform'))))


def main() -> int:
    smoke_selfhosted()
    smoke_saas()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
