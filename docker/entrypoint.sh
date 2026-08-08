#!/bin/sh
set -e
# Platform + attach default tenant (idempotent) + migrate all
if [ "${APP_EDITION}" = "saas" ] && [ -n "$PLATFORM_DATABASE_URL" ]; then
  python scripts/migrate_single_to_saas.py --slug "${LEGACY_TENANT_SLUG:-nika}" --name "${LEGACY_TENANT_NAME:-Nika Fitness}" || true
  python scripts/run_migrations.py --platform --all-tenants --seed-admin
else
  python scripts/run_migrations.py --legacy --seed-admin
fi
exec gunicorn -b 0.0.0.0:8000 -w 2 --timeout 120 wsgi:app
