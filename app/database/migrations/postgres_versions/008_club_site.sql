-- Club public site content (landing)

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
