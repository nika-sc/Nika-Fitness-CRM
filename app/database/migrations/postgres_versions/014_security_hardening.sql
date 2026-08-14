-- Security hardening: no plaintext portal passwords, shared auth audit/lockout

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
