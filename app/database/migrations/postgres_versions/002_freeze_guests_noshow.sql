-- Freeze memberships, guest visits, no-show settings

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

INSERT INTO app_settings (key, value) VALUES
    ('freeze_max_days_per_year', '30'),
    ('noshow_deduct_visit', 'true')
ON CONFLICT (key) DO NOTHING;
