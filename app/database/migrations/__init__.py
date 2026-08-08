"""PostgreSQL numbered SQL migrations (tenant DBs)."""
from __future__ import annotations

import logging
import re
from pathlib import Path

from app.database.connection import get_db_connection, tenant_context

logger = logging.getLogger(__name__)

VERSIONS_DIR = Path(__file__).resolve().parent / 'postgres_versions'
VERSION_RE = re.compile(r'^(\d{3})_(.+)\.sql$')


def _ensure_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations_pg (
                version VARCHAR(16) PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )


def _applied(conn) -> set[str]:
    with conn.cursor() as cur:
        cur.execute('SELECT version FROM schema_migrations_pg')
        return {r[0] for r in cur.fetchall()}


def list_migration_files() -> list[tuple[str, str, Path]]:
    items = []
    if not VERSIONS_DIR.exists():
        return items
    for path in sorted(VERSIONS_DIR.glob('*.sql')):
        m = VERSION_RE.match(path.name)
        if not m:
            continue
        items.append((m.group(1), m.group(2), path))
    return items


def run_migrations(dsn: str | None = None, slug: str = '_') -> list[str]:
    """Apply tenant migrations. If dsn given, runs inside that tenant context."""

    def _run() -> list[str]:
        applied_now: list[str] = []
        with get_db_connection() as conn:
            _ensure_table(conn)
            done = _applied(conn)
            for version, name, path in list_migration_files():
                if version in done:
                    continue
                sql = path.read_text(encoding='utf-8')
                logger.info('Applying migration %s_%s (tenant=%s)', version, name, slug)
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cur.execute(
                        'INSERT INTO schema_migrations_pg (version, name) VALUES (%s, %s)',
                        (version, name),
                    )
                applied_now.append(f'{version}_{name}')
        return applied_now

    if dsn:
        with tenant_context(slug, dsn):
            return _run()
    return _run()
