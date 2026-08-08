"""Club public site content + landing payload."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlencode, urlparse

from app.database.connection import execute, execute_returning, fetch_all, fetch_one
from app.services.membership_service import MembershipService
from app.services.schedule_service import ScheduleService
from app.services.settings_service import SettingsService
from app.services.trainer_service import TrainerService

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
                updated_at = NOW()
            WHERE id = 1
            RETURNING *
            """,
            (
                (data.get('headline') or '').strip(),
                (data.get('about_text') or '').strip(),
                (data.get('phone') or '').strip(),
                (data.get('address') or '').strip(),
                (data.get('hours_text') or '').strip(),
                data.get('hero_photo_path'),
                map_url,
                theme['preset'],
                theme['accent'],
                data.get('background_photo_path'),
                theme['overlay'],
                bool(data.get('is_published')),
            ),
        )

    @staticmethod
    def list_photos() -> list[dict]:
        return fetch_all(
            'SELECT * FROM club_site_photos ORDER BY sort_order, id'
        )

    @staticmethod
    def add_photo(photo_path: str, caption: str = '') -> dict:
        mx = fetch_one('SELECT COALESCE(MAX(sort_order), 0)::int AS m FROM club_site_photos')
        return execute_returning(
            """
            INSERT INTO club_site_photos (photo_path, caption, sort_order)
            VALUES (%s, %s, %s) RETURNING *
            """,
            (photo_path, (caption or '').strip(), (mx['m'] if mx else 0) + 1),
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
        for t in trainers:
            t['upcoming'] = ClubSiteService.upcoming_for_trainer(t['id'], 4)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())
        map_url = (site.get('map_embed_url') or '').strip() or DEFAULT_MAP_EMBED
        return {
            'site': site,
            'theme': ClubSiteService.theme(site),
            'club_name': club_name,
            'photos': ClubSiteService.list_photos(),
            'plans': MembershipService.list_plans(active_only=True),
            'trainers': trainers,
            'sessions': ScheduleService.list_sessions(week_start),
            'week_start': week_start.date(),
            'load_by_day': ClubSiteService.load_by_day(14),
            'map_embed_url': map_url,
        }
