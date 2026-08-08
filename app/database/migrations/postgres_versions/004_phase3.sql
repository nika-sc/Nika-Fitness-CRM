-- Phase 3: zones, corporate, cash/debts, lockers, PT commissions

CREATE TABLE IF NOT EXISTS access_zones (
    id SERIAL PRIMARY KEY,
    code VARCHAR(40) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS plan_zone_access (
    plan_id INTEGER NOT NULL REFERENCES membership_plans(id) ON DELETE CASCADE,
    zone_id INTEGER NOT NULL REFERENCES access_zones(id) ON DELETE CASCADE,
    PRIMARY KEY (plan_id, zone_id)
);

CREATE TABLE IF NOT EXISTS corporate_accounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    contact_phone VARCHAR(40) NOT NULL DEFAULT '',
    contact_email VARCHAR(200) NOT NULL DEFAULT '',
    seats_limit INTEGER NOT NULL DEFAULT 10,
    note TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE members ADD COLUMN IF NOT EXISTS corporate_id INTEGER REFERENCES corporate_accounts(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS cash_shifts (
    id SERIAL PRIMARY KEY,
    opened_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    closed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    opening_cents INTEGER NOT NULL DEFAULT 0,
    closing_cents INTEGER,
    note TEXT NOT NULL DEFAULT '',
    status VARCHAR(40) NOT NULL DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS debts (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    amount_cents INTEGER NOT NULL,
    paid_cents INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(40) NOT NULL DEFAULT 'open',
    note TEXT NOT NULL DEFAULT '',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_debts_member ON debts (member_id, status);

CREATE TABLE IF NOT EXISTS lockers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(40) NOT NULL UNIQUE,
    zone VARCHAR(80) NOT NULL DEFAULT 'main',
    status VARCHAR(40) NOT NULL DEFAULT 'free',
    member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    assigned_at TIMESTAMPTZ,
    note TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS trainer_commission_rules (
    id SERIAL PRIMARY KEY,
    trainer_id INTEGER NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    percent NUMERIC(5,2) NOT NULL DEFAULT 40.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (trainer_id)
);

INSERT INTO access_zones (code, name) VALUES
    ('gym', 'Тренажёрный зал'),
    ('pool', 'Бассейн'),
    ('spa', 'SPA')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (name, description) VALUES
    ('manage_zones', 'Зоны доступа'),
    ('manage_corporate', 'Корпоративные контракты'),
    ('manage_cash', 'Касса и долги'),
    ('manage_lockers', 'Шкафчики')
ON CONFLICT (name) DO NOTHING;

INSERT INTO role_permissions (role, permission_id)
SELECT r.role, p.id FROM (VALUES ('admin'),('owner'),('reception')) AS r(role)
CROSS JOIN permissions p
WHERE p.name IN ('manage_zones','manage_corporate','manage_cash','manage_lockers')
ON CONFLICT DO NOTHING;
