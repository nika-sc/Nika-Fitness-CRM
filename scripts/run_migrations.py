#!/usr/bin/env python3
"""Apply platform and/or tenant PostgreSQL migrations."""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, '.env'))
except ImportError:
    pass

from werkzeug.security import generate_password_hash

from app.database.connection import (
    build_tenant_dsn,
    saas_enabled,
    tenant_context,
    fetch_one,
    execute,
)
from app.database.migrations import run_migrations


def seed_admin() -> None:
    existing = fetch_one('SELECT id FROM users WHERE username = %s', ('admin',))
    if existing:
        print('Admin user already exists')
        return
    password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    execute(
        """
        INSERT INTO users (username, password_hash, full_name, role, is_active)
        VALUES (%s, %s, %s, %s, TRUE)
        """,
        ('admin', generate_password_hash(password), 'Администратор', 'admin'),
    )
    print(f'Created admin / {password} (change immediately)')


def migrate_tenant(slug: str, db_name: str, seed: bool = False) -> None:
    dsn = build_tenant_dsn(db_name)
    applied = run_migrations(dsn=dsn, slug=slug)
    if applied:
        print(f'[{slug}] Applied:', ', '.join(applied))
    else:
        print(f'[{slug}] No new migrations')
    if seed:
        with tenant_context(slug, dsn):
            seed_admin()


def main() -> int:
    parser = argparse.ArgumentParser(description='Nika Fitness migrations')
    parser.add_argument('--platform', action='store_true', help='Run platform (control-plane) migrations')
    parser.add_argument('--tenant', metavar='SLUG', help='Migrate one tenant by slug')
    parser.add_argument('--all-tenants', action='store_true', help='Migrate all active tenants')
    parser.add_argument('--legacy', action='store_true', help='Migrate DATABASE_URL (single-tenant / no SaaS)')
    parser.add_argument('--seed-admin', action='store_true', help='Seed admin user after tenant migrate')
    args = parser.parse_args()

    if not any([args.platform, args.tenant, args.all_tenants, args.legacy]):
        if saas_enabled():
            args.platform = True
            args.all_tenants = True
        else:
            args.legacy = True
            args.seed_admin = True

    if args.platform:
        try:
            from app.saas.migrations import run_platform_migrations
        except ModuleNotFoundError:
            print('SaaS package not available; platform migrations skipped', file=sys.stderr)
            return 1
        if not saas_enabled():
            print('APP_EDITION=saas and PLATFORM_DATABASE_URL required', file=sys.stderr)
            return 1
        applied = run_platform_migrations()
        if applied:
            print('Platform applied:', ', '.join(applied))
        else:
            print('Platform: no new migrations')

    if args.legacy:
        from app.database.connection import get_legacy_database_url
        dsn = get_legacy_database_url()
        applied = run_migrations(dsn=dsn, slug='legacy')
        if applied:
            print('Legacy applied:', ', '.join(applied))
        else:
            print('Legacy: no new migrations')
        if args.seed_admin:
            with tenant_context('legacy', dsn):
                seed_admin()

    if args.tenant or args.all_tenants:
        try:
            from app.saas.services.tenant_service import TenantService
        except ModuleNotFoundError:
            print('SaaS package not available', file=sys.stderr)
            return 1
        if not saas_enabled():
            print('APP_EDITION=saas and PLATFORM_DATABASE_URL required', file=sys.stderr)
            return 1
        if args.tenant:
            row = TenantService.get_by_slug(args.tenant)
            if not row:
                print(f'Tenant not found: {args.tenant}', file=sys.stderr)
                return 1
            tenants = [row]
        else:
            tenants = TenantService.list_active()
        for t in tenants:
            migrate_tenant(t['slug'], t['db_name'], seed=args.seed_admin)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
