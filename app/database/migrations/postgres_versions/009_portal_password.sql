-- Member portal password (email delivery + staff-visible for ops)

ALTER TABLE members
    ADD COLUMN IF NOT EXISTS portal_password_hash TEXT,
    ADD COLUMN IF NOT EXISTS portal_password_plain VARCHAR(64);

COMMENT ON COLUMN members.portal_password_plain IS
    'Ops/test: last issued portal password (shown in CRM). Auth uses portal_password_hash.';
