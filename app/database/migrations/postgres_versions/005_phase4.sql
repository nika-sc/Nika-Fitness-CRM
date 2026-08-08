-- Phase 4: segments, loyalty, NPS, leads

CREATE TABLE IF NOT EXISTS segments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    rule_key VARCHAR(80) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS loyalty_accounts (
    member_id INTEGER PRIMARY KEY REFERENCES members(id) ON DELETE CASCADE,
    points INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS loyalty_ledger (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    delta INTEGER NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_loyalty_ledger_member ON loyalty_ledger (member_id, created_at DESC);

CREATE TABLE IF NOT EXISTS nps_responses (
    id SERIAL PRIMARY KEY,
    member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    score INTEGER NOT NULL,
    comment TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(200) NOT NULL,
    phone VARCHAR(40) NOT NULL DEFAULT '',
    email VARCHAR(200) NOT NULL DEFAULT '',
    source VARCHAR(80) NOT NULL DEFAULT 'manual',
    status VARCHAR(40) NOT NULL DEFAULT 'new',
    assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads (status);

INSERT INTO segments (name, rule_key, description)
SELECT * FROM (VALUES
    ('Спящие 14 дней', 'sleeping_14', 'Не было чекина 14+ дней'),
    ('Спящие 30 дней', 'sleeping_30', 'Не было чекина 30+ дней'),
    ('Истекает за 7 дней', 'expiring_7', 'Абонемент истекает в течение 7 дней')
) AS v(name, rule_key, description)
WHERE NOT EXISTS (SELECT 1 FROM segments LIMIT 1);

INSERT INTO permissions (name, description) VALUES
    ('manage_loyalty', 'Программа лояльности'),
    ('manage_leads', 'Лиды и воронка'),
    ('view_segments', 'Сегменты клиентов')
ON CONFLICT (name) DO NOTHING;

INSERT INTO role_permissions (role, permission_id)
SELECT r.role, p.id FROM (VALUES ('admin'),('owner'),('reception')) AS r(role)
CROSS JOIN permissions p
WHERE p.name IN ('manage_loyalty','manage_leads','view_segments')
ON CONFLICT DO NOTHING;
