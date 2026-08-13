-- Starter pack: optional modules off, cash↔payments, gym presence

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
