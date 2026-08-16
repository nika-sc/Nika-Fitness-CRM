-- Public booking requests from the club site (no member portal account required)

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
    -- snapshot of what the visitor picked: survives session/slot deletion
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
