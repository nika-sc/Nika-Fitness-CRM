-- Richer club-site copy: separate hero/about, amenities, gallery heading

ALTER TABLE club_site
    ADD COLUMN IF NOT EXISTS hero_kicker VARCHAR(80) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS hero_lead TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS cta_label VARCHAR(80) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS about_heading VARCHAR(120) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS gallery_heading VARCHAR(120) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS footer_tagline VARCHAR(160) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS amenities JSONB NOT NULL DEFAULT '[]'::jsonb;

UPDATE club_site
SET hero_lead = about_text
WHERE COALESCE(hero_lead, '') = '' AND COALESCE(about_text, '') <> '';
