-- Nika Fitness CRM initial schema

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(200) NOT NULL DEFAULT '',
    role VARCHAR(40) NOT NULL DEFAULT 'reception',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(80) NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role VARCHAR(40) NOT NULL,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role, permission_id)
);

CREATE TABLE IF NOT EXISTS members (
    id SERIAL PRIMARY KEY,
    card_number VARCHAR(32) NOT NULL UNIQUE,
    full_name VARCHAR(200) NOT NULL,
    phone VARCHAR(40) NOT NULL DEFAULT '',
    email VARCHAR(200) NOT NULL DEFAULT '',
    photo_path TEXT,
    notes TEXT NOT NULL DEFAULT '',
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_members_phone ON members (phone);
CREATE INDEX IF NOT EXISTS idx_members_full_name ON members (full_name);

CREATE TABLE IF NOT EXISTS membership_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    duration_days INTEGER NOT NULL DEFAULT 30,
    visit_limit INTEGER,
    price_cents INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memberships (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    plan_id INTEGER REFERENCES membership_plans(id) ON DELETE SET NULL,
    starts_on DATE NOT NULL,
    ends_on DATE NOT NULL,
    visits_remaining INTEGER,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_memberships_member ON memberships (member_id);
CREATE INDEX IF NOT EXISTS idx_memberships_ends_on ON memberships (ends_on);

CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    membership_id INTEGER REFERENCES memberships(id) ON DELETE SET NULL,
    amount_cents INTEGER NOT NULL,
    method VARCHAR(40) NOT NULL DEFAULT 'cash',
    paid_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    note TEXT NOT NULL DEFAULT '',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_payments_member ON payments (member_id);
CREATE INDEX IF NOT EXISTS idx_payments_paid_at ON payments (paid_at);

CREATE TABLE IF NOT EXISTS trainers (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(200) NOT NULL,
    phone VARCHAR(40) NOT NULL DEFAULT '',
    email VARCHAR(200) NOT NULL DEFAULT '',
    bio TEXT NOT NULL DEFAULT '',
    photo_path TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS class_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    default_price_cents INTEGER NOT NULL DEFAULT 0,
    default_capacity INTEGER NOT NULL DEFAULT 15,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS class_sessions (
    id SERIAL PRIMARY KEY,
    class_type_id INTEGER NOT NULL REFERENCES class_types(id) ON DELETE CASCADE,
    trainer_id INTEGER REFERENCES trainers(id) ON DELETE SET NULL,
    room_name VARCHAR(120) NOT NULL DEFAULT 'Зал 1',
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    capacity INTEGER NOT NULL DEFAULT 15,
    price_cents INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_class_sessions_starts ON class_sessions (starts_at);

CREATE TABLE IF NOT EXISTS class_bookings (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES class_sessions(id) ON DELETE CASCADE,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    status VARCHAR(40) NOT NULL DEFAULT 'booked',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, member_id)
);

CREATE TABLE IF NOT EXISTS checkins (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    membership_id INTEGER REFERENCES memberships(id) ON DELETE SET NULL,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source VARCHAR(40) NOT NULL DEFAULT 'reception',
    alert_level VARCHAR(40) NOT NULL DEFAULT 'ok',
    message TEXT NOT NULL DEFAULT '',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_checkins_checked_at ON checkins (checked_at);
CREATE INDEX IF NOT EXISTS idx_checkins_member ON checkins (member_id);

CREATE TABLE IF NOT EXISTS staff_alerts (
    id SERIAL PRIMARY KEY,
    member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    checkin_id INTEGER REFERENCES checkins(id) ON DELETE SET NULL,
    alert_type VARCHAR(60) NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    severity VARCHAR(20) NOT NULL DEFAULT 'warning',
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_staff_alerts_created ON staff_alerts (created_at DESC);

CREATE TABLE IF NOT EXISTS email_reminders (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    membership_id INTEGER NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
    reminder_key VARCHAR(80) NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (membership_id, reminder_key)
);

CREATE TABLE IF NOT EXISTS app_settings (
    key VARCHAR(80) PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

INSERT INTO permissions (name, description) VALUES
    ('view_members', 'Просмотр клиентов'),
    ('manage_members', 'Управление клиентами'),
    ('view_memberships', 'Просмотр абонементов'),
    ('manage_memberships', 'Управление абонементами и оплатами'),
    ('checkin', 'Чекин на ресепшене'),
    ('view_schedule', 'Просмотр расписания'),
    ('manage_schedule', 'Управление расписанием и записями'),
    ('view_trainers', 'Просмотр тренеров'),
    ('manage_trainers', 'Управление тренерами'),
    ('view_alerts', 'Просмотр алертов'),
    ('view_reports', 'Просмотр отчётов'),
    ('manage_users', 'Управление сотрудниками'),
    ('manage_settings', 'Настройки системы')
ON CONFLICT (name) DO NOTHING;

-- admin / owner: all permissions
INSERT INTO role_permissions (role, permission_id)
SELECT 'admin', id FROM permissions
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role, permission_id)
SELECT 'owner', id FROM permissions
ON CONFLICT DO NOTHING;

-- reception
INSERT INTO role_permissions (role, permission_id)
SELECT 'reception', id FROM permissions
WHERE name IN (
    'view_members', 'manage_members', 'view_memberships', 'manage_memberships',
    'checkin', 'view_schedule', 'manage_schedule', 'view_trainers',
    'view_alerts', 'view_reports'
)
ON CONFLICT DO NOTHING;

-- trainer
INSERT INTO role_permissions (role, permission_id)
SELECT 'trainer', id FROM permissions
WHERE name IN (
    'view_members', 'view_memberships', 'view_schedule', 'view_trainers', 'view_alerts'
)
ON CONFLICT DO NOTHING;

INSERT INTO membership_plans (name, description, duration_days, visit_limit, price_cents)
SELECT * FROM (VALUES
    ('Месяц безлимит', '30 дней безлимитных посещений', 30, NULL::INTEGER, 450000),
    ('12 визитов', 'Абонемент на 12 посещений, 45 дней', 45, 12, 350000),
    ('Разовое', 'Одно посещение', 1, 1, 80000)
) AS v(name, description, duration_days, visit_limit, price_cents)
WHERE NOT EXISTS (SELECT 1 FROM membership_plans LIMIT 1);

INSERT INTO class_types (name, description, default_price_cents, default_capacity)
SELECT * FROM (VALUES
    ('Йога', 'Групповая йога', 90000, 12),
    ('Functional', 'Функциональный тренинг', 100000, 15),
    ('Пилатес', 'Пилатес-мат', 95000, 12)
) AS v(name, description, default_price_cents, default_capacity)
WHERE NOT EXISTS (SELECT 1 FROM class_types LIMIT 1);

INSERT INTO app_settings (key, value) VALUES
    ('club_name', 'Nika Fitness'),
    ('expiring_days', '7')
ON CONFLICT DO NOTHING;
