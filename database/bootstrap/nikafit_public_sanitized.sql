-- Nika Fitness CRM bootstrap (sanitized)
-- Tip schema: 002_freeze_guests_noshow
-- Prefer empty DB + scripts/run_migrations.py for existing installs.

CREATE TABLE IF NOT EXISTS schema_migrations_pg (
    version VARCHAR(16) PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
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
    source VARCHAR(40) NOT NULL DEFAULT 'staff',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cancelled_at TIMESTAMPTZ,
    UNIQUE (session_id, member_id)
);
CREATE INDEX IF NOT EXISTS idx_class_bookings_created_source
    ON class_bookings (created_at DESC, source, status);
CREATE INDEX IF NOT EXISTS idx_class_bookings_member_status
    ON class_bookings (member_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS checkins (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    membership_id INTEGER REFERENCES memberships(id) ON DELETE SET NULL,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source VARCHAR(40) NOT NULL DEFAULT 'reception',
    alert_level VARCHAR(40) NOT NULL DEFAULT 'ok',
    message TEXT NOT NULL DEFAULT '',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    checked_out_at TIMESTAMPTZ
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
    ('expiring_days', '7'),
    ('freeze_max_days_per_year', '30'),
    ('noshow_deduct_visit', 'true'),
    ('portal_cancel_before_hours', '2')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS membership_freezes (
    id SERIAL PRIMARY KEY,
    membership_id INTEGER NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
    starts_on DATE NOT NULL DEFAULT CURRENT_DATE,
    ends_on DATE,
    days_used INTEGER NOT NULL DEFAULT 0,
    reason TEXT NOT NULL DEFAULT '',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_membership_freezes_membership ON membership_freezes (membership_id);
CREATE INDEX IF NOT EXISTS idx_membership_freezes_starts ON membership_freezes (starts_on);

CREATE TABLE IF NOT EXISTS guest_visits (
    id SERIAL PRIMARY KEY,
    guest_name VARCHAR(200) NOT NULL,
    guest_phone VARCHAR(40) NOT NULL DEFAULT '',
    host_member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    payment_id INTEGER REFERENCES payments(id) ON DELETE SET NULL,
    amount_cents INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_guest_visits_created ON guest_visits (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_guest_visits_host ON guest_visits (host_member_id);

-- Phase 2–6 (synced from postgres_versions 003–007)

CREATE TABLE IF NOT EXISTS class_waitlist (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES class_sessions(id) ON DELETE CASCADE,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'waiting',
    notified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, member_id)
);
CREATE INDEX IF NOT EXISTS idx_waitlist_session ON class_waitlist (session_id, status);

CREATE TABLE IF NOT EXISTS member_portal_otps (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    phone VARCHAR(40) NOT NULL,
    code VARCHAR(12) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_portal_otps_phone ON member_portal_otps (phone);

CREATE TABLE IF NOT EXISTS pt_packages (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    trainer_id INTEGER REFERENCES trainers(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL DEFAULT 'PT пакет',
    sessions_total INTEGER NOT NULL DEFAULT 10,
    sessions_left INTEGER NOT NULL DEFAULT 10,
    price_cents INTEGER NOT NULL DEFAULT 0,
    expires_on DATE,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pt_packages_member ON pt_packages (member_id);

CREATE TABLE IF NOT EXISTS pt_sessions (
    id SERIAL PRIMARY KEY,
    package_id INTEGER NOT NULL REFERENCES pt_packages(id) ON DELETE CASCADE,
    trainer_id INTEGER REFERENCES trainers(id) ON DELETE SET NULL,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ,
    status VARCHAR(40) NOT NULL DEFAULT 'scheduled',
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pt_sessions_trainer ON pt_sessions (trainer_id, starts_at);

CREATE TABLE IF NOT EXISTS message_outbox (
    id SERIAL PRIMARY KEY,
    channel VARCHAR(40) NOT NULL DEFAULT 'log',
    recipient VARCHAR(200) NOT NULL DEFAULT '',
    template_key VARCHAR(80) NOT NULL DEFAULT '',
    payload TEXT NOT NULL DEFAULT '',
    status VARCHAR(40) NOT NULL DEFAULT 'sent',
    error TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_message_outbox_created ON message_outbox (created_at DESC);

INSERT INTO permissions (name, description) VALUES
    ('manage_waitlist', 'Лист ожидания занятий'),
    ('view_portal_admin', 'Админ ЛК клиентов'),
    ('manage_pt', 'PT-пакеты и сессии'),
    ('manage_messaging', 'Сообщения SMS/Telegram/outbox')
ON CONFLICT (name) DO NOTHING;

INSERT INTO role_permissions (role, permission_id)
SELECT 'admin', id FROM permissions
WHERE name IN ('manage_waitlist','view_portal_admin','manage_pt','manage_messaging')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role, permission_id)
SELECT 'owner', id FROM permissions
WHERE name IN ('manage_waitlist','view_portal_admin','manage_pt','manage_messaging')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role, permission_id)
SELECT 'reception', id FROM permissions
WHERE name IN ('manage_waitlist','manage_pt','manage_messaging')
ON CONFLICT DO NOTHING;

INSERT INTO app_settings (key, value) VALUES
    ('loyalty_points_per_visit', '1'),
    ('loyalty_points_per_100rub', '1'),
    ('enforce_medical_cert', 'false'),
    ('default_access_zone', 'gym')
ON CONFLICT (key) DO NOTHING;

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

-- Club public site (008)
CREATE TABLE IF NOT EXISTS club_site (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    headline VARCHAR(200) NOT NULL DEFAULT '',
    about_text TEXT NOT NULL DEFAULT '',
    phone VARCHAR(40) NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    hours_text TEXT NOT NULL DEFAULT '',
    hero_photo_path TEXT,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS club_site_photos (
    id SERIAL PRIMARY KEY,
    photo_path TEXT NOT NULL,
    caption VARCHAR(200) NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO club_site (id, headline, about_text, is_published)
SELECT 1, COALESCE(
    (SELECT value FROM app_settings WHERE key = 'club_name' LIMIT 1),
    'Фитнес-клуб'
), '', FALSE
WHERE NOT EXISTS (SELECT 1 FROM club_site WHERE id = 1);

INSERT INTO permissions (name, description) VALUES
    ('manage_club_site', 'Редактирование публичного сайта клуба')
ON CONFLICT (name) DO NOTHING;

INSERT INTO role_permissions (role, permission_id)
SELECT r.role, p.id FROM (VALUES ('admin'),('owner'),('reception')) AS r(role)
CROSS JOIN permissions p
WHERE p.name = 'manage_club_site'
ON CONFLICT DO NOTHING;

ALTER TABLE members
    ADD COLUMN IF NOT EXISTS portal_password_hash TEXT,
    ADD COLUMN IF NOT EXISTS portal_password_plain VARCHAR(64);

ALTER TABLE club_site
    ADD COLUMN IF NOT EXISTS map_embed_url TEXT NOT NULL DEFAULT '';

ALTER TABLE club_site
    ADD COLUMN IF NOT EXISTS theme_preset VARCHAR(24) NOT NULL DEFAULT 'inferno',
    ADD COLUMN IF NOT EXISTS accent_color VARCHAR(7) NOT NULL DEFAULT '#ff3b30',
    ADD COLUMN IF NOT EXISTS background_photo_path TEXT,
    ADD COLUMN IF NOT EXISTS background_overlay INTEGER NOT NULL DEFAULT 72;

ALTER TABLE club_site DROP CONSTRAINT IF EXISTS club_site_theme_preset_check;
ALTER TABLE club_site ADD CONSTRAINT club_site_theme_preset_check
    CHECK (theme_preset IN ('inferno', 'midnight', 'graphite'));

ALTER TABLE club_site DROP CONSTRAINT IF EXISTS club_site_accent_color_check;
ALTER TABLE club_site ADD CONSTRAINT club_site_accent_color_check
    CHECK (accent_color ~ '^#[0-9A-Fa-f]{6}$');

ALTER TABLE club_site DROP CONSTRAINT IF EXISTS club_site_background_overlay_check;
ALTER TABLE club_site ADD CONSTRAINT club_site_background_overlay_check
    CHECK (background_overlay BETWEEN 0 AND 90);

ALTER TABLE club_site
    ADD COLUMN IF NOT EXISTS hero_kicker VARCHAR(80) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS hero_lead TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS cta_label VARCHAR(80) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS about_heading VARCHAR(120) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS gallery_heading VARCHAR(120) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS footer_tagline VARCHAR(160) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS amenities JSONB NOT NULL DEFAULT '[]'::jsonb;

UPDATE club_site
SET hero_lead = about_text
WHERE COALESCE(hero_lead, '') = '' AND COALESCE(about_text, '') <> '';

ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS cash_shift_id INTEGER REFERENCES cash_shifts(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_payments_cash_shift ON payments (cash_shift_id);

ALTER TABLE checkins
    ADD COLUMN IF NOT EXISTS checked_out_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_checkins_open_presence
    ON checkins (checked_at DESC)
    WHERE checked_out_at IS NULL;

INSERT INTO app_settings (key, value) VALUES
    ('module_leads', 'false'),
    ('module_loyalty', 'false'),
    ('module_pt', 'false'),
    ('module_spa', 'false'),
    ('module_lockers', 'false'),
    ('module_corporate', 'false'),
    ('module_payments_online', 'false'),
    ('module_zones', 'false'),
    ('module_messaging', 'false'),
    ('module_branches', 'false'),
    ('gym_presence_hours', '4')
ON CONFLICT (key) DO NOTHING;

DELETE FROM role_permissions
WHERE role = 'reception'
  AND permission_id IN (
    SELECT id FROM permissions WHERE name IN (
        'manage_leads',
        'manage_loyalty',
        'view_segments',
        'manage_pt',
        'manage_spa',
        'manage_lockers',
        'manage_corporate',
        'manage_payments_online',
        'manage_zones',
        'manage_messaging',
        'manage_branches'
    )
  );

UPDATE members SET portal_password_plain = NULL WHERE portal_password_plain IS NOT NULL;
COMMENT ON COLUMN members.portal_password_plain IS
    'Deprecated, always NULL. Portal auth uses portal_password_hash only.';

CREATE TABLE IF NOT EXISTS auth_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(40) NOT NULL,
    client_key VARCHAR(255) NOT NULL DEFAULT '',
    username VARCHAR(128) NOT NULL DEFAULT '',
    ip VARCHAR(64) NOT NULL DEFAULT '',
    user_id INTEGER,
    member_id INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_auth_events_lockout
    ON auth_events (client_key, event_type, created_at DESC);

CREATE TABLE IF NOT EXISTS cash_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    kind VARCHAR(20) NOT NULL CHECK (kind IN ('income', 'expense')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS cash_transactions (
    id SERIAL PRIMARY KEY,
    amount_cents INTEGER NOT NULL,
    kind VARCHAR(20) NOT NULL CHECK (kind IN ('income', 'expense')),
    method VARCHAR(20) NOT NULL DEFAULT 'cash',
    category_id INTEGER REFERENCES cash_categories(id) ON DELETE SET NULL,
    member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    payment_id INTEGER REFERENCES payments(id) ON DELETE SET NULL,
    cash_shift_id INTEGER REFERENCES cash_shifts(id) ON DELETE SET NULL,
    paid_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    note TEXT NOT NULL DEFAULT '',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_cash_tx_paid ON cash_transactions (paid_at);
CREATE INDEX IF NOT EXISTS idx_cash_tx_kind ON cash_transactions (kind);
INSERT INTO cash_categories (name, kind)
SELECT v.name, v.kind FROM (VALUES
    ('Абонемент', 'income'),
    ('Гостевой визит', 'income'),
    ('PT', 'income'),
    ('Прочий приход', 'income'),
    ('Зарплата', 'expense'),
    ('Закупка', 'expense'),
    ('Прочий расход', 'expense')
) AS v(name, kind)
WHERE NOT EXISTS (SELECT 1 FROM cash_categories c WHERE c.name = v.name AND c.kind = v.kind);

ALTER TABLE trainers ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_trainers_user ON trainers (user_id) WHERE user_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS trainer_slots (
    id SERIAL PRIMARY KEY,
    trainer_id INTEGER NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open'
        CONSTRAINT trainer_slots_status_check
        CHECK (status IN ('open', 'pending', 'booked', 'done', 'no_show', 'cancelled')),
    place VARCHAR(120) NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    source VARCHAR(20) NOT NULL DEFAULT 'trainer'
        CHECK (source IN ('trainer', 'staff', 'portal')),
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    booked_at TIMESTAMPTZ,
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_trainer_slots_trainer ON trainer_slots (trainer_id, starts_at);
CREATE INDEX IF NOT EXISTS idx_trainer_slots_open ON trainer_slots (status, starts_at);
CREATE INDEX IF NOT EXISTS idx_trainer_slots_member ON trainer_slots (member_id, starts_at);

INSERT INTO permissions (name, description) VALUES
    ('manage_trainer_slots', 'Слоты тренера и запись на персоналку')
ON CONFLICT (name) DO NOTHING;

INSERT INTO role_permissions (role, permission_id)
SELECT r.role, p.id FROM (VALUES ('admin'), ('owner'), ('reception'), ('trainer')) AS r(role)
CROSS JOIN permissions p
WHERE p.name = 'manage_trainer_slots'
ON CONFLICT DO NOTHING;

INSERT INTO app_settings (key, value) VALUES
    ('module_trainer_slots', 'true'),
    ('pt_max_active_bookings', '3')
ON CONFLICT (key) DO NOTHING;

ALTER TABLE club_site
    ADD COLUMN IF NOT EXISTS booking_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS booking_note VARCHAR(300) NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS site_booking_requests (
    id SERIAL PRIMARY KEY,
    kind VARCHAR(20) NOT NULL DEFAULT 'trial'
        CHECK (kind IN ('class', 'trainer', 'trial')),
    session_id INTEGER REFERENCES class_sessions(id) ON DELETE SET NULL,
    slot_id INTEGER REFERENCES trainer_slots(id) ON DELETE SET NULL,
    trainer_id INTEGER REFERENCES trainers(id) ON DELETE SET NULL,
    member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    full_name VARCHAR(200) NOT NULL,
    phone VARCHAR(40) NOT NULL,
    comment VARCHAR(500) NOT NULL DEFAULT '',
    target_label VARCHAR(200) NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'contacted', 'confirmed', 'declined', 'spam')),
    staff_note VARCHAR(500) NOT NULL DEFAULT '',
    processed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_site_requests_status ON site_booking_requests (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_site_requests_phone ON site_booking_requests (phone, created_at DESC);

INSERT INTO permissions (name, description) VALUES
    ('manage_site_requests', 'Заявки с сайта клуба')
ON CONFLICT (name) DO NOTHING;

INSERT INTO role_permissions (role, permission_id)
SELECT r.role, p.id FROM (VALUES ('admin'), ('owner'), ('reception')) AS r(role)
CROSS JOIN permissions p
WHERE p.name = 'manage_site_requests'
ON CONFLICT DO NOTHING;

INSERT INTO schema_migrations_pg (version, name)
VALUES
    ('001', 'initial'),
    ('002', 'freeze_guests_noshow'),
    ('003', 'phase2'),
    ('004', 'phase3'),
    ('005', 'phase4'),
    ('006', 'phase5'),
    ('007', 'phase6'),
    ('008', 'club_site'),
    ('009', 'portal_password'),
    ('010', 'club_map'),
    ('011', 'club_theme'),
    ('012', 'booking_tracking'),
    ('013', 'starter_pack'),
    ('014', 'security_hardening'),
    ('015', 'cash_articles'),
    ('016', 'trainer_slots'),
    ('017', 'trainer_slot_confirm'),
    ('018', 'club_site_content'),
    ('019', 'site_booking_requests')
ON CONFLICT (version) DO NOTHING;
