"""PostgreSQL pools: per-tenant / legacy (contextvars). Platform pool lives in app.saas.db."""
from __future__ import annotations

import importlib.util
import logging
import os
import re
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from typing import Any, Iterator, Optional
from urllib.parse import urlparse, urlunparse

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

logger = logging.getLogger(__name__)

_tenant_dsn: ContextVar[Optional[str]] = ContextVar('tenant_dsn', default=None)
_tenant_slug: ContextVar[Optional[str]] = ContextVar('tenant_slug', default=None)

_pools: dict[str, ThreadedConnectionPool] = {}
_pools_lock = threading.Lock()


def get_legacy_database_url() -> str:
    url = (os.environ.get('DATABASE_URL') or '').strip()
    if not url:
        raise RuntimeError('DATABASE_URL is required (legacy single-tenant)')
    return url


@lru_cache(maxsize=1)
def _saas_available() -> bool:
    return importlib.util.find_spec('app.saas') is not None


def saas_enabled() -> bool:
    """True when SaaS package is present, APP_EDITION=saas, and PLATFORM_DATABASE_URL is set."""
    if not _saas_available():
        return False
    edition = (os.environ.get('APP_EDITION') or 'selfhosted').strip().lower()
    if edition != 'saas':
        return False
    return bool((os.environ.get('PLATFORM_DATABASE_URL') or '').strip())


def tenant_dsn_template() -> str:
    tmpl = (os.environ.get('TENANT_DATABASE_URL_TEMPLATE') or '').strip()
    if tmpl:
        return tmpl
    platform = (os.environ.get('PLATFORM_DATABASE_URL') or '').strip()
    if not platform:
        raise RuntimeError('PLATFORM_DATABASE_URL or TENANT_DATABASE_URL_TEMPLATE required')
    parsed = urlparse(platform)
    base = parsed._replace(path='/__DB__')
    return urlunparse(base).replace('/__DB__', '/{db_name}')


def build_tenant_dsn(db_name: str) -> str:
    safe = (db_name or '').strip()
    if not re.match(r'^[a-zA-Z0-9_]+$', safe):
        raise ValueError('Invalid database name')
    return tenant_dsn_template().format(db_name=safe)


def get_tenant_dsn() -> str:
    dsn = _tenant_dsn.get()
    if dsn:
        return dsn
    if not saas_enabled():
        return get_legacy_database_url()
    raise RuntimeError('No tenant database context')


def get_tenant_slug() -> Optional[str]:
    return _tenant_slug.get()


def set_tenant_context(slug: str | None, dsn: str | None) -> tuple:
    """Set tenant context; returns tokens for reset."""
    t1 = _tenant_slug.set(slug)
    t2 = _tenant_dsn.set(dsn)
    return t1, t2


def reset_tenant_context(tokens: tuple) -> None:
    t1, t2 = tokens
    _tenant_slug.reset(t1)
    _tenant_dsn.reset(t2)


@contextmanager
def tenant_context(slug: str, dsn: str) -> Iterator[None]:
    tokens = set_tenant_context(slug, dsn)
    try:
        yield
    finally:
        reset_tenant_context(tokens)


def _pool_limits() -> tuple[int, int]:
    minconn = max(1, int(os.environ.get('PG_POOL_MINCONN', '1')))
    maxconn = max(minconn, int(os.environ.get('PG_POOL_MAXCONN', '8')))
    return minconn, maxconn


def _get_pool_for_dsn(dsn: str) -> ThreadedConnectionPool:
    with _pools_lock:
        pool = _pools.get(dsn)
        if pool is not None:
            return pool
        minconn, maxconn = _pool_limits()
        pool = ThreadedConnectionPool(minconn=minconn, maxconn=maxconn, dsn=dsn)
        _pools[dsn] = pool
        logger.info('PostgreSQL pool ready dsn_host=%s min=%s max=%s', urlparse(dsn).hostname, minconn, maxconn)
        return pool


def _get_pool() -> ThreadedConnectionPool:
    return _get_pool_for_dsn(get_tenant_dsn())


@contextmanager
def get_db_connection():
    pool = _get_pool()
    conn = None
    for attempt in range(3):
        try:
            conn = pool.getconn()
            break
        except Exception as exc:
            logger.warning('getconn failed attempt=%s: %s', attempt + 1, exc)
            time.sleep(0.1)
    if conn is None:
        raise RuntimeError('Unable to get DB connection')
    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        pool.putconn(conn)


def fetch_one(sql: str, params: tuple | list | None = None) -> Optional[dict]:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or ())
            row = cur.fetchone()
            return dict(row) if row else None


def fetch_all(sql: str, params: tuple | list | None = None) -> list[dict]:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or ())
            return [dict(r) for r in cur.fetchall()]


def execute(sql: str, params: tuple | list | None = None) -> int:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.rowcount


def execute_returning(sql: str, params: tuple | list | None = None) -> Any:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or ())
            row = cur.fetchone()
            return dict(row) if row else None
