-- Trainer confirms portal requests before the slot counts as booked

ALTER TABLE trainer_slots ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;

ALTER TABLE trainer_slots DROP CONSTRAINT IF EXISTS trainer_slots_status_check;
ALTER TABLE trainer_slots ADD CONSTRAINT trainer_slots_status_check
    CHECK (status IN ('open', 'pending', 'booked', 'done', 'no_show', 'cancelled'));

UPDATE trainer_slots SET confirmed_at = booked_at
WHERE status IN ('booked', 'done', 'no_show') AND confirmed_at IS NULL;

INSERT INTO app_settings (key, value) VALUES
    ('pt_max_active_bookings', '3')
ON CONFLICT (key) DO NOTHING;
