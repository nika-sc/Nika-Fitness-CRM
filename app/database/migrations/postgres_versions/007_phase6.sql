-- Phase 6: medical, SPA/bar/kids, kiosk, push

CREATE TABLE IF NOT EXISTS medical_certificates (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    issued_on DATE,
    expires_on DATE NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_medical_certs_member ON medical_certificates (member_id, expires_on DESC);

CREATE TABLE IF NOT EXISTS spa_services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    category VARCHAR(40) NOT NULL DEFAULT 'spa',
    duration_min INTEGER NOT NULL DEFAULT 60,
    price_cents INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS spa_bookings (
    id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES spa_services(id) ON DELETE CASCADE,
    member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'booked',
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bar_sales (
    id SERIAL PRIMARY KEY,
    item_name VARCHAR(120) NOT NULL,
    amount_cents INTEGER NOT NULL,
    member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    cash_shift_id INTEGER REFERENCES cash_shifts(id) ON DELETE SET NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS kids_slots (
    id SERIAL PRIMARY KEY,
    parent_member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    child_name VARCHAR(120) NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'booked',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS kiosk_devices (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    token VARCHAR(64) NOT NULL UNIQUE,
    branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id SERIAL PRIMARY KEY,
    member_id INTEGER REFERENCES members(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    keys_json TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO spa_services (name, category, duration_min, price_cents)
SELECT * FROM (VALUES
    ('Массаж 60 мин', 'spa', 60, 350000),
    ('Солярий 10 мин', 'spa', 10, 50000),
    ('Вода 0.5л', 'bar', 0, 8000)
) AS v(name, category, duration_min, price_cents)
WHERE NOT EXISTS (SELECT 1 FROM spa_services LIMIT 1);

INSERT INTO permissions (name, description) VALUES
    ('manage_spa', 'SPA / бар / детский клуб'),
    ('manage_kiosk', 'Киоск самообслуживания')
ON CONFLICT (name) DO NOTHING;

INSERT INTO role_permissions (role, permission_id)
SELECT r.role, p.id FROM (VALUES ('admin'),('owner'),('reception')) AS r(role)
CROSS JOIN permissions p
WHERE p.name IN ('manage_spa','manage_kiosk')
ON CONFLICT DO NOTHING;
