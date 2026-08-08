-- Club site: Yandex map embed URL for contacts

ALTER TABLE club_site
    ADD COLUMN IF NOT EXISTS map_embed_url TEXT NOT NULL DEFAULT '';
