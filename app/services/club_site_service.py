"""Club public site content + landing payload."""
from __future__ import annotations

import json
import re
from datetime import datetime
from itertools import groupby
from urllib.parse import parse_qs, urlencode, urlparse

from psycopg2.extras import Json

from app.database.connection import execute, execute_returning, fetch_all, fetch_one
from app.services.feature_flags_service import FeatureFlagsService
from app.services.membership_service import MembershipService
from app.services.schedule_service import ScheduleService
from app.services.settings_service import SettingsService
from app.services.trainer_service import TrainerService
from app.services.trainer_slot_service import TrainerSlotService

# Proff Sport / Adler default (Yandex constructor)
DEFAULT_MAP_EMBED = (
    'https://yandex.ru/map-widget/v1/'
    '?um=constructor%3Aa5463c0830982a5d60a54366fd69ed50faadaa97711095940f4a33ad5db2a587'
    '&source=constructor'
)

_ALLOWED_MAP_HOSTS = frozenset({
    'yandex.ru',
    'www.yandex.ru',
    'yandex.com',
    'www.yandex.com',
    'api-maps.yandex.ru',
})

THEME_PRESETS = {
    'inferno': {
        'label': 'Inferno',
        'surface': '#17090b',
        'surface_rgb': '23, 9, 11',
        'text': '#fff7f4',
        'muted': '#d4aaa5',
        'default_accent': '#ff3b30',
    },
    'midnight': {
        'label': 'Midnight',
        'surface': '#071221',
        'surface_rgb': '7, 18, 33',
        'text': '#f1f7ff',
        'muted': '#9db2cc',
        'default_accent': '#2e8cff',
    },
    'graphite': {
        'label': 'Graphite',
        'surface': '#111214',
        'surface_rgb': '17, 18, 20',
        'text': '#f6f6f2',
        'muted': '#aaaeb5',
        'default_accent': '#b8ff3d',
    },
}
_HEX_COLOR_RE = re.compile(r'^#[0-9a-fA-F]{6}$')

MAX_GALLERY_PHOTOS = 24
MAX_AMENITIES = 6

AMENITY_ICONS = (
    ('dumbbell', 'Силовая зона'),
    ('heart-pulse', 'Кардио'),
    ('activity', 'Функционал'),
    ('person-walking', 'Студия'),
    ('bicycle', 'Вело / сайкл'),
    ('lightning-charge', 'HIIT'),
    ('trophy', 'Соревнования'),
    ('droplet', 'Бассейн / вода'),
    ('water', 'Восстановление'),
    ('fire', 'Сауна / тепло'),
    ('snow', 'Крио / холод'),
    ('wind', 'Воздух / йога'),
    ('sun', 'Терраса / свет'),
    ('cup-hot', 'Бар / кафе'),
    ('music-note-beamed', 'Музыка'),
    ('people', 'Сообщество'),
    ('shield-check', 'Безопасность'),
    ('clock', 'Круглосуточно'),
)
AMENITY_ICON_SET = frozenset(item[0] for item in AMENITY_ICONS)


class ClubSiteService:
    @staticmethod
    def normalize_theme(preset: str, accent: str, overlay) -> dict:
        preset = (preset or 'inferno').strip().lower()
        if preset not in THEME_PRESETS:
            raise ValueError('Неизвестная тема клуба')
        accent = (accent or THEME_PRESETS[preset]['default_accent']).strip()
        if not _HEX_COLOR_RE.fullmatch(accent):
            raise ValueError('Акцентный цвет должен быть в формате #RRGGBB')
        try:
            overlay_value = int(overlay)
        except (TypeError, ValueError) as exc:
            raise ValueError('Затемнение должно быть числом от 0 до 90') from exc
        if not 0 <= overlay_value <= 90:
            raise ValueError('Затемнение должно быть от 0 до 90')
        return {
            'preset': preset,
            'accent': accent.lower(),
            'overlay': overlay_value,
            **THEME_PRESETS[preset],
        }

    @staticmethod
    def normalize_amenities(raw) -> list[dict]:
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                raw = []
        if not isinstance(raw, list):
            raw = []
        out: list[dict] = []
        for item in raw[:MAX_AMENITIES]:
            if not isinstance(item, dict):
                continue
            title = (item.get('title') or '').strip()[:80]
            if not title:
                continue
            icon = (item.get('icon') or 'dumbbell').strip()
            if icon.startswith('bi-'):
                icon = icon[3:]
            if icon not in AMENITY_ICON_SET:
                icon = 'dumbbell'
            text = (item.get('text') or '').strip()[:200]
            out.append({'icon': icon, 'title': title, 'text': text})
        return out

    @staticmethod
    def amenities_for_form(site: dict | None = None) -> list[dict]:
        rows = ClubSiteService.normalize_amenities((site or {}).get('amenities'))
        while len(rows) < MAX_AMENITIES:
            rows.append({'icon': 'dumbbell', 'title': '', 'text': ''})
        return rows

    @staticmethod
    def theme(site: dict | None = None) -> dict:
        site = site or ClubSiteService.get()
        theme = ClubSiteService.normalize_theme(
            site.get('theme_preset') or 'inferno',
            site.get('accent_color') or '#ff3b30',
            site.get('background_overlay', 72),
        )
        theme['background_photo_path'] = (
            site.get('background_photo_path')
            or site.get('hero_photo_path')
            or 'foto/gallery-1.jpg'
        )
        return theme

    @staticmethod
    def normalize_map_url(raw: str) -> str:
        """Accept iframe src or Yandex Maps share link; return safe embed URL or ''."""
        url = (raw or '').strip()
        if not url:
            return ''
        # Allow pasting full iframe HTML by extracting src=
        if 'src=' in url.lower() and 'http' in url:
            import re
            m = re.search(r'''src\s*=\s*["']([^"']+)["']''', url, re.I)
            if m:
                url = m.group(1).strip()
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            raise ValueError('Ссылка на карту должна начинаться с https://')
        host = (parsed.hostname or '').lower()
        if host not in _ALLOWED_MAP_HOSTS and not host.endswith('.yandex.ru'):
            raise ValueError('Разрешены только ссылки Яндекс.Карт (yandex.ru)')
        # Convert constructor page URL → map-widget
        qs = parse_qs(parsed.query)
        um = (qs.get('um') or [None])[0]
        if um and 'map-widget' not in (parsed.path or ''):
            params = {'um': um, 'source': 'constructor'}
            ll = (qs.get('ll') or [None])[0]
            z = (qs.get('z') or [None])[0]
            if ll:
                params['ll'] = ll
            if z:
                params['z'] = z
            return 'https://yandex.ru/map-widget/v1/?' + urlencode(params)
        return url

    @staticmethod
    def ensure_row() -> dict:
        row = fetch_one('SELECT * FROM club_site WHERE id = 1')
        if row:
            return row
        name = SettingsService.get('club_name', 'Фитнес-клуб')
        return execute_returning(
            """
            INSERT INTO club_site (id, headline, about_text, is_published, map_embed_url)
            VALUES (1, %s, '', FALSE, %s)
            RETURNING *
            """,
            (name, DEFAULT_MAP_EMBED),
        )

    @staticmethod
    def get() -> dict:
        return ClubSiteService.ensure_row()

    @staticmethod
    def update(data: dict) -> dict:
        ClubSiteService.ensure_row()
        map_url = ClubSiteService.normalize_map_url(data.get('map_embed_url') or '')
        theme = ClubSiteService.normalize_theme(
            data.get('theme_preset') or 'inferno',
            data.get('accent_color') or '#ff3b30',
            data.get('background_overlay', 72),
        )
        amenities = ClubSiteService.normalize_amenities(data.get('amenities'))
        return execute_returning(
            """
            UPDATE club_site SET
                headline = %s,
                about_text = %s,
                phone = %s,
                address = %s,
                hours_text = %s,
                hero_photo_path = COALESCE(%s, hero_photo_path),
                map_embed_url = %s,
                theme_preset = %s,
                accent_color = %s,
                background_photo_path = COALESCE(%s, background_photo_path),
                background_overlay = %s,
                is_published = %s,
                hero_kicker = %s,
                hero_lead = %s,
                cta_label = %s,
                about_heading = %s,
                gallery_heading = %s,
                footer_tagline = %s,
                amenities = %s,
                booking_enabled = %s,
                booking_note = %s,
                updated_at = NOW()
            WHERE id = 1
            RETURNING *
            """,
            (
                (data.get('headline') or '').strip()[:200],
                (data.get('about_text') or '').strip(),
                (data.get('phone') or '').strip()[:40],
                (data.get('address') or '').strip(),
                (data.get('hours_text') or '').strip(),
                data.get('hero_photo_path'),
                map_url,
                theme['preset'],
                theme['accent'],
                data.get('background_photo_path'),
                theme['overlay'],
                bool(data.get('is_published')),
                (data.get('hero_kicker') or '').strip()[:80],
                (data.get('hero_lead') or '').strip(),
                (data.get('cta_label') or '').strip()[:80],
                (data.get('about_heading') or '').strip()[:120],
                (data.get('gallery_heading') or '').strip()[:120],
                (data.get('footer_tagline') or '').strip()[:160],
                Json(amenities),
                bool(data.get('booking_enabled')),
                (data.get('booking_note') or '').strip()[:300],
            ),
        )

    @staticmethod
    def list_photos() -> list[dict]:
        return fetch_all(
            'SELECT * FROM club_site_photos ORDER BY sort_order, id'
        )

    @staticmethod
    def photo_count() -> int:
        row = fetch_one('SELECT COUNT(*)::int AS c FROM club_site_photos')
        return int(row['c']) if row else 0

    @staticmethod
    def add_photo(photo_path: str, caption: str = '') -> dict:
        if ClubSiteService.photo_count() >= MAX_GALLERY_PHOTOS:
            raise ValueError(f'Можно загрузить не больше {MAX_GALLERY_PHOTOS} фото')
        mx = fetch_one('SELECT COALESCE(MAX(sort_order), 0)::int AS m FROM club_site_photos')
        return execute_returning(
            """
            INSERT INTO club_site_photos (photo_path, caption, sort_order)
            VALUES (%s, %s, %s) RETURNING *
            """,
            (photo_path, (caption or '').strip()[:200], (mx['m'] if mx else 0) + 1),
        )

    @staticmethod
    def update_photo_caption(photo_id: int, caption: str) -> None:
        execute(
            'UPDATE club_site_photos SET caption = %s WHERE id = %s',
            ((caption or '').strip()[:200], photo_id),
        )

    @staticmethod
    def move_photo(photo_id: int, direction: str) -> None:
        photos = ClubSiteService.list_photos()
        idx = next((i for i, p in enumerate(photos) if p['id'] == photo_id), None)
        if idx is None:
            return
        swap = idx - 1 if direction == 'up' else idx + 1
        if swap < 0 or swap >= len(photos):
            return
        a = photos[idx]
        b = photos[swap]
        execute(
            """
            UPDATE club_site_photos
            SET sort_order = CASE id
                WHEN %s THEN %s
                WHEN %s THEN %s
            END
            WHERE id IN (%s, %s)
            """,
            (a['id'], b['sort_order'], b['id'], a['sort_order'], a['id'], b['id']),
        )

    @staticmethod
    def delete_photo(photo_id: int) -> None:
        execute('DELETE FROM club_site_photos WHERE id = %s', (photo_id,))

    @staticmethod
    def load_by_day(days: int = 14) -> list[dict]:
        return fetch_all(
            """
            SELECT d::date AS day, COALESCE(c.cnt, 0)::int AS cnt
            FROM generate_series(
                CURRENT_DATE - (%s::int - 1),
                CURRENT_DATE,
                '1 day'::interval
            ) AS d
            LEFT JOIN (
                SELECT checked_at::date AS day, COUNT(*)::int AS cnt
                FROM checkins
                WHERE checked_at >= CURRENT_DATE - (%s::int - 1)
                GROUP BY checked_at::date
            ) c ON c.day = d::date
            ORDER BY day
            """,
            (days, days),
        )

    @staticmethod
    def upcoming_for_trainer(trainer_id: int, limit: int = 5) -> list[dict]:
        return fetch_all(
            """
            SELECT s.starts_at, s.ends_at, ct.name AS class_name, s.capacity,
                   (SELECT COUNT(*) FROM class_bookings b
                    WHERE b.session_id = s.id AND b.status = 'booked') AS booked_count
            FROM class_sessions s
            JOIN class_types ct ON ct.id = s.class_type_id
            WHERE s.trainer_id = %s AND s.starts_at >= NOW()
            ORDER BY s.starts_at
            LIMIT %s
            """,
            (trainer_id, limit),
        )

    @staticmethod
    def public_payload(require_published: bool = True) -> dict | None:
        site = ClubSiteService.get()
        if require_published and not site.get('is_published'):
            return None
        club_name = SettingsService.get('club_name', site.get('headline') or 'Клуб')
        trainers = TrainerService.list_all(active_only=True)
        slots_enabled = FeatureFlagsService.is_enabled('module_trainer_slots')
        for t in trainers:
            t['upcoming'] = ClubSiteService.upcoming_for_trainer(t['id'], 4)
            t['open_slots'] = (
                TrainerSlotService.list_open(t['id'], days=21, limit=8) if slots_enabled else []
            )
        # Rolling week: visitors should always land on classes they can still book.
        week_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        map_url = (site.get('map_embed_url') or '').strip() or DEFAULT_MAP_EMBED
        sessions = ScheduleService.list_sessions(week_start)
        for item in sessions:
            starts = item['starts_at']
            moment = datetime.now(starts.tzinfo) if getattr(starts, 'tzinfo', None) else datetime.now()
            item['is_past'] = starts < moment
            item['is_full'] = int(item.get('booked_count') or 0) >= int(item.get('capacity') or 0)
        sessions_by_day = []
        for day, items in groupby(sessions, key=lambda s: s['starts_at'].date()):
            sessions_by_day.append({'day': day, 'lessons': list(items)})
        return {
            'site': site,
            'theme': ClubSiteService.theme(site),
            'club_name': club_name,
            'photos': ClubSiteService.list_photos(),
            'amenities': ClubSiteService.normalize_amenities(site.get('amenities')),
            'plans': MembershipService.list_plans(active_only=True),
            'trainers': trainers,
            'sessions': sessions,
            'sessions_by_day': sessions_by_day,
            'trainer_open_slots': {
                t['id']: [
                    {'id': s['id'], 'label': s['starts_at'].strftime('%d.%m · %H:%M')}
                    for s in t['open_slots']
                ]
                for t in trainers
                if t['open_slots']
            },
            'week_start': week_start.date(),
            'load_by_day': ClubSiteService.load_by_day(14),
            'map_embed_url': map_url,
        }
