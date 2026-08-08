-- Portal booking tracking: source, timestamps, cancel policy

ALTER TABLE class_bookings
    ADD COLUMN IF NOT EXISTS source VARCHAR(40) NOT NULL DEFAULT 'staff',
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_class_bookings_created_source
    ON class_bookings (created_at DESC, source, status);

CREATE INDEX IF NOT EXISTS idx_class_bookings_member_status
    ON class_bookings (member_id, status, created_at DESC);

INSERT INTO app_settings (key, value) VALUES
    ('portal_cancel_before_hours', '2')
ON CONFLICT (key) DO NOTHING;
