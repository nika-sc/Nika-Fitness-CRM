-- Phase 5: payment intents, branches

CREATE TABLE IF NOT EXISTS branches (
    id SERIAL PRIMARY KEY,
    code VARCHAR(40) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    address TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE class_sessions ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE checkins ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS payment_intents (
    id SERIAL PRIMARY KEY,
    member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'RUB',
    purpose VARCHAR(120) NOT NULL DEFAULT 'membership',
    status VARCHAR(40) NOT NULL DEFAULT 'pending',
    provider VARCHAR(40) NOT NULL DEFAULT 'stub',
    external_id VARCHAR(120) NOT NULL DEFAULT '',
    meta TEXT NOT NULL DEFAULT '',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    paid_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_payment_intents_status ON payment_intents (status, created_at DESC);

INSERT INTO branches (code, name) VALUES ('main', 'Основной клуб')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (name, description) VALUES
    ('manage_branches', 'Филиалы'),
    ('manage_payments_online', 'Онлайн-оплаты / эквайринг')
ON CONFLICT (name) DO NOTHING;

INSERT INTO role_permissions (role, permission_id)
SELECT r.role, p.id FROM (VALUES ('admin'),('owner'),('reception')) AS r(role)
CROSS JOIN permissions p
WHERE p.name IN ('manage_branches','manage_payments_online')
ON CONFLICT DO NOTHING;
