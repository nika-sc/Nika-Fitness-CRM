#!/usr/bin/env python3
"""Mobile viewport audit for Fitness CRM + brand hub after the nika-ui engine.

Usage:
  python scripts/audit_mobile_fitness.py
  python scripts/audit_mobile_fitness.py --base https://fitness.nika-crm.ru --hub https://nika-crm.ru
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'assets' / 'mobile'
DEFAULT_BASE = 'https://fitness.nika-crm.ru'
DEFAULT_HUB = 'https://nika-crm.ru'
SLUG = 'nika'
STAFF_USER = 'admin'
STAFF_PASS = 'admin123'
PORTAL_LOGIN = 'client@demo-nika.fit'
PORTAL_PASS = 'client123'

VIEWPORTS = (
    ('390', {'width': 390, 'height': 844}),
    ('360', {'width': 360, 'height': 740}),
)

NAV_OPEN_SELECTORS = (
    '#hubNav.is-open',
    '#publicNav.is-open',
    '#clubNav.is-open',
    '#portalNav.is-open',
    '.nika-nav.is-open',
)


def _csrf(html: str) -> str | None:
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if m:
        return m.group(1)
    m = re.search(r'value="([^"]+)"[^>]*name="csrf_token"', html)
    return m.group(1) if m else None


def _overflow(page) -> dict:
    return page.evaluate(
        """() => {
          const doc = document.documentElement;
          const body = document.body;
          const sw = Math.max(doc.scrollWidth, body ? body.scrollWidth : 0);
          const cw = window.innerWidth;
          return {
            scrollWidth: sw,
            innerWidth: cw,
            horizontal_overflow: sw > cw + 1
          };
        }"""
    )


def _visible(page, selector: str) -> bool:
    loc = page.locator(selector).first
    try:
        return bool(loc.count()) and loc.is_visible()
    except Exception:
        return False


def _menu_is_open(page) -> bool:
    for sel in NAV_OPEN_SELECTORS:
        if _visible(page, sel):
            return True
    return bool(
        page.evaluate(
            """() => {
              const box = document.querySelector('#app-drawer');
              return !!(box && box.checked);
            }"""
        )
    )


def _try_open_menu(page) -> bool:
    if _visible(page, '.nika-nav-toggle'):
        try:
            page.locator('.nika-nav-toggle').first.click(timeout=2500)
            page.wait_for_timeout(400)
            if _menu_is_open(page):
                return True
        except Exception:
            pass
    if _visible(page, 'label[for="app-drawer"]'):
        try:
            page.locator('label[for="app-drawer"]').first.click(timeout=2500)
            page.wait_for_timeout(400)
            if _menu_is_open(page):
                return True
        except Exception:
            pass
    return False


def _try_close_menu(page) -> None:
    if _visible(page, '.nika-nav-toggle') and _menu_is_open(page):
        try:
            page.locator('.nika-nav-toggle').first.click(timeout=1500)
            page.wait_for_timeout(200)
            return
        except Exception:
            pass
    if _visible(page, '.drawer-overlay') and _menu_is_open(page):
        try:
            box = page.locator('.drawer-overlay').first.bounding_box()
            if box:
                page.mouse.click(box['x'] + box['width'] - 12, box['y'] + box['height'] / 2)
            else:
                page.locator('.drawer-overlay').first.click(timeout=1500, force=True)
            page.wait_for_timeout(200)
            return
        except Exception:
            pass
    if _visible(page, 'label[for="app-drawer"]') and _menu_is_open(page):
        try:
            page.locator('label[for="app-drawer"]').first.click(timeout=1500)
            page.wait_for_timeout(200)
        except Exception:
            pass


def _toggle_expected(page) -> bool:
    return _visible(page, '.nika-nav-toggle') or _visible(page, 'label[for="app-drawer"]')


def _probe_club_modal(page) -> dict:
    info = {'tried': False, 'opened': False, 'closed': False}
    opener = page.locator(
        '.club-hero-copy [data-booking-open], .club-week-book, main .club-booking-cta [data-booking-open]'
    ).first
    modal = page.locator('#club-booking-modal')
    try:
        if not opener.count() or not modal.count():
            return info
        info['tried'] = True
        info['opened'] = page.evaluate(
            """() => {
              const btn = document.querySelector('.club-hero-copy [data-booking-open], .club-week-book, main .club-booking-cta [data-booking-open]');
              const modal = document.getElementById('club-booking-modal');
              if (!btn || !modal) return false;
              btn.click();
              return modal.classList.contains('is-open');
            }"""
        )
        if info['opened']:
            page.wait_for_timeout(200)
            info['closed'] = page.evaluate(
                """() => {
                  const modal = document.getElementById('club-booking-modal');
                  if (!modal) return false;
                  const closer = modal.querySelector('[data-nika-dismiss="modal"]');
                  if (closer) closer.click();
                  else if (window.NikaModal) NikaModal.hide(modal);
                  else modal.classList.remove('is-open', 'modal-open');
                  return !modal.classList.contains('is-open');
                }"""
            )
    except Exception as exc:
        info['error'] = str(exc)
    return info


def _audit_page(page, *, url: str, name: str, results: list[dict], extra=None) -> None:
    entry = {
        'name': name,
        'url': url,
        'ok': False,
        'final_url': '',
        'horizontal_overflow': False,
        'scrollWidth': 0,
        'innerWidth': 0,
        'menu_expected': False,
        'menu_opened': False,
        'error': None,
        'shot': f'{name}.png',
        'shot_menu': None,
    }
    try:
        resp = None
        last_exc = None
        for _attempt in range(2):
            try:
                resp = page.goto(url, wait_until='domcontentloaded', timeout=25000)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
        if last_exc:
            raise last_exc
        page.wait_for_timeout(700)
        entry['final_url'] = page.url
        entry['status'] = resp.status if resp else None
        metrics = _overflow(page)
        entry.update(metrics)
        shot = OUT / f'{name}.png'
        page.screenshot(path=str(shot), full_page=True, type='png')
        entry['menu_expected'] = _toggle_expected(page)
        opened = _try_open_menu(page)
        entry['menu_opened'] = opened
        if opened:
            menu_shot = OUT / f'{name}-menu.png'
            page.screenshot(path=str(menu_shot), full_page=True, type='png')
            entry['shot_menu'] = menu_shot.name
            _try_close_menu(page)
        if extra:
            extra(page, entry)
        status_ok = (entry.get('status') or 200) < 400
        menu_ok = (not entry['menu_expected']) or entry['menu_opened']
        extra_ok = entry.get('extra_ok', True)
        entry['ok'] = status_ok and not entry['horizontal_overflow'] and menu_ok and extra_ok
        if entry['menu_expected'] and not entry['menu_opened']:
            entry['error'] = entry.get('error') or 'menu toggle visible but did not open'
    except Exception as exc:
        entry['error'] = str(exc)
        entry['ok'] = False
    results.append(entry)
    flag = 'FAIL' if not entry['ok'] else 'PASS'
    err = str(entry.get('error') or '').encode('ascii', 'replace').decode('ascii')
    print(
        f'[{flag}] {name}: overflow={entry["horizontal_overflow"]} '
        f'sw={entry.get("scrollWidth")} menu={entry["menu_opened"]}/'
        f'exp={entry["menu_expected"]} status={entry.get("status")} err={err or None}',
        flush=True,
    )


def _staff_login(page, base: str) -> None:
    page.goto(f"{base.rstrip('/')}/t/{SLUG}/login", wait_until='domcontentloaded')
    token = _csrf(page.content())
    page.fill('input[name="username"]', STAFF_USER)
    page.fill('input[name="password"]', STAFF_PASS)
    if token:
        page.evaluate(
            """(t) => {
              const el = document.querySelector('input[name="csrf_token"]');
              if (el) el.value = t;
            }""",
            token,
        )
    page.click('button[type="submit"], input[type="submit"]')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(400)


def _portal_login(page, base: str) -> None:
    page.goto(f"{base.rstrip('/')}/t/{SLUG}/portal/", wait_until='domcontentloaded')
    page.wait_for_timeout(300)
    if page.locator('input[name="login"]').count() == 0:
        return
    page.fill('input[name="login"]', PORTAL_LOGIN)
    page.fill('input[name="password"]', PORTAL_PASS)
    token = _csrf(page.content())
    if token:
        page.evaluate(
            """(t) => {
              const el = document.querySelector('input[name="csrf_token"]');
              if (el) el.value = t;
            }""",
            token,
        )
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(500)


def _club_extra(page, entry: dict) -> None:
    modal = _probe_club_modal(page)
    entry['club_modal'] = modal
    if modal.get('tried') and not (modal.get('opened') and modal.get('closed')):
        entry['extra_ok'] = False
        entry['error'] = entry.get('error') or f'club booking modal {modal}'


def _run_suite(browser, viewport: dict, tag: str, base: str, hub: str) -> list[dict]:
    results: list[dict] = []
    context = browser.new_context(
        viewport=viewport,
        device_scale_factor=2,
        has_touch=True,
        user_agent=(
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
            'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 '
            'Mobile/15E148 Safari/604.1'
        ),
    )
    page = context.new_page()

    _audit_page(page, url=hub.rstrip('/') + '/', name=f'{tag}-hub', results=results)

    public_pages = [
        ('landing', '/'),
        ('login', '/login'),
        ('demo', '/demo'),
        ('docs', '/docs'),
        ('blog', '/blog'),
        ('staff-login', f'/t/{SLUG}/login'),
        ('club', f'/club/{SLUG}/'),
        ('portal-login', f'/t/{SLUG}/portal/'),
    ]
    for name, path in public_pages:
        extra = _club_extra if name == 'club' else None
        _audit_page(
            page,
            url=base.rstrip('/') + path,
            name=f'{tag}-{name}',
            results=results,
            extra=extra,
        )

    try:
        _staff_login(page, base)
        for name, path in [
            ('dashboard', f'/t/{SLUG}/'),
            ('reception', f'/t/{SLUG}/reception/'),
            ('members', f'/t/{SLUG}/members/'),
            ('schedule', f'/t/{SLUG}/schedule/'),
        ]:
            _audit_page(
                page,
                url=base.rstrip('/') + path,
                name=f'{tag}-{name}',
                results=results,
            )
    except Exception as exc:
        results.append(
            {
                'name': f'{tag}-staff-session',
                'ok': False,
                'error': f'staff login failed: {exc}',
                'horizontal_overflow': False,
                'menu_expected': False,
                'menu_opened': False,
            }
        )
        print(f'[FAIL] {tag}-staff-session: {exc}')

    portal = context.new_page()
    try:
        _portal_login(portal, base)
        _audit_page(
            portal,
            url=f"{base.rstrip('/')}/t/{SLUG}/portal/",
            name=f'{tag}-portal-home',
            results=results,
        )
    except Exception as exc:
        results.append(
            {
                'name': f'{tag}-portal-home',
                'ok': False,
                'error': f'portal login/audit failed: {exc}',
                'horizontal_overflow': False,
                'menu_expected': False,
                'menu_opened': False,
            }
        )
        print(f'[FAIL] {tag}-portal-home: {exc}')

    context.close()
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description='Mobile audit for Fitness CRM + hub')
    parser.add_argument('--base', default=DEFAULT_BASE, help='Fitness demo base URL')
    parser.add_argument('--hub', default=DEFAULT_HUB, help='Brand hub URL')
    parser.add_argument(
        '--viewport',
        action='append',
        choices=[item[0] for item in VIEWPORTS],
        help='Limit to one or more viewport tags (default: both 390 and 360)',
    )
    args = parser.parse_args()
    base = args.base.rstrip('/')
    hub = args.hub.rstrip('/')
    chosen = args.viewport or [item[0] for item in VIEWPORTS]
    viewports = [item for item in VIEWPORTS if item[0] in chosen]

    OUT.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for tag, viewport in viewports:
            print(f'\n=== viewport {tag} {viewport} ===', flush=True)
            results.extend(_run_suite(browser, viewport, tag, base, hub))
        browser.close()

    failed = [r for r in results if not r.get('ok')]
    report = {
        'base': base,
        'hub': hub,
        'viewports': {tag: vp for tag, vp in viewports},
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'pass': len(results) - len(failed),
        'fail': len(failed),
        'results': results,
    }
    report_path = OUT / 'report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nReport: {report_path}  PASS={report["pass"]} FAIL={report["fail"]}')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
