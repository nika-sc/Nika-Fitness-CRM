-- Phase 2: waitlist, portal OTP, PT packages, message outbox

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
