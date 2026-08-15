-- Trainer cabinet: link trainer card to staff account + open slots for personal training

ALTER TABLE trainers ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_trainers_user ON trainers (user_id) WHERE user_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS trainer_slots (
    id SERIAL PRIMARY KEY,
    trainer_id INTEGER NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'booked', 'done', 'no_show', 'cancelled')),
    place VARCHAR(120) NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    source VARCHAR(20) NOT NULL DEFAULT 'trainer'
        CHECK (source IN ('trainer', 'staff', 'portal')),
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    booked_at TIMESTAMPTZ,
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
    ('module_trainer_slots', 'true')
ON CONFLICT (key) DO NOTHING;
