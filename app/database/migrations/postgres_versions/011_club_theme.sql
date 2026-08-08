-- Shared visual theme for public club site and member portal

ALTER TABLE club_site
    ADD COLUMN IF NOT EXISTS theme_preset VARCHAR(24) NOT NULL DEFAULT 'inferno',
    ADD COLUMN IF NOT EXISTS accent_color VARCHAR(7) NOT NULL DEFAULT '#ff3b30',
    ADD COLUMN IF NOT EXISTS background_photo_path TEXT,
    ADD COLUMN IF NOT EXISTS background_overlay INTEGER NOT NULL DEFAULT 72;

ALTER TABLE club_site DROP CONSTRAINT IF EXISTS club_site_theme_preset_check;
ALTER TABLE club_site ADD CONSTRAINT club_site_theme_preset_check
    CHECK (theme_preset IN ('inferno', 'midnight', 'graphite'));

ALTER TABLE club_site DROP CONSTRAINT IF EXISTS club_site_accent_color_check;
ALTER TABLE club_site ADD CONSTRAINT club_site_accent_color_check
    CHECK (accent_color ~ '^#[0-9A-Fa-f]{6}$');

ALTER TABLE club_site DROP CONSTRAINT IF EXISTS club_site_background_overlay_check;
ALTER TABLE club_site ADD CONSTRAINT club_site_background_overlay_check
    CHECK (background_overlay BETWEEN 0 AND 90);
