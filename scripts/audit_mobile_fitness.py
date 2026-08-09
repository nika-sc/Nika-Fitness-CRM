#!/usr/bin/env python3
"""Mobile viewport audit for Fitness CRM (screenshots + horizontal overflow).

Usage:
  python scripts/audit_mobile_fitness.py
  python scripts/audit_mobile_fitness.py --base https://fitness.nika-crm.ru
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
OUT = ROOT / "docs" / "assets" / "mobile"
DEFAULT_BASE = "https://fitness.nika-crm.ru"
SLUG = "nika"
STAFF_USER = "admin"
STAFF_PASS = "admin123"
PORTAL_LOGIN = "smelkov2008@yandex.ru"
PORTAL_PASS = "client123"

VIEWPORT = {"width": 390, "height": 844}


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


def _try_open_menu(page) -> bool:
    selectors = [
        ".nika-admin [data-lte-toggle='sidebar']",
        ".app-header [data-lte-toggle='sidebar']",
        "a.nav-link[data-lte-toggle='sidebar']",
        ".navbar-toggler",
        "button.navbar-toggler",
        "[data-bs-toggle='collapse'][data-bs-target*='Nav']",
        "[data-bs-toggle='offcanvas']",
    ]
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            if loc.count() and loc.is_visible():
                loc.click(timeout=2500)
                page.wait_for_timeout(450)
                return True
        except Exception:
            continue
    return False


def _audit_page(page, *, base: str, path: str, name: str, results: list[dict]) -> None:
    url = base.rstrip("/") + path
    entry = {
        "name": name,
        "path": path,
        "url": url,
        "ok": False,
        "final_url": "",
        "horizontal_overflow": False,
        "scrollWidth": 0,
        "innerWidth": 0,
        "menu_opened": False,
        "error": None,
        "shot": f"{name}.png",
        "shot_menu": None,
    }
    try:
        resp = page.goto(url, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(500)
        entry["final_url"] = page.url
        entry["status"] = resp.status if resp else None
        metrics = _overflow(page)
        entry.update(metrics)
        shot = OUT / f"{name}.png"
        page.screenshot(path=str(shot), full_page=True, type="png")
        opened = _try_open_menu(page)
        entry["menu_opened"] = opened
        if opened:
            menu_shot = OUT / f"{name}-menu.png"
            page.screenshot(path=str(menu_shot), full_page=True, type="png")
            entry["shot_menu"] = menu_shot.name
            # close menu if possible (toggle again)
            _try_open_menu(page)
        status_ok = (entry.get("status") or 200) < 400
        entry["ok"] = status_ok and not entry["horizontal_overflow"]
    except Exception as exc:
        entry["error"] = str(exc)
        entry["ok"] = False
    results.append(entry)
    flag = "FAIL" if not entry["ok"] else "PASS"
    print(
        f"[{flag}] {name}: overflow={entry['horizontal_overflow']} "
        f"sw={entry.get('scrollWidth')} menu={entry['menu_opened']} "
        f"status={entry.get('status')} err={entry.get('error')}"
    )


def _staff_login(page, base: str) -> None:
    page.goto(f"{base.rstrip('/')}/t/{SLUG}/login", wait_until="networkidle")
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
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(400)


def _portal_login(page, base: str) -> None:
    page.goto(f"{base.rstrip('/')}/t/{SLUG}/portal/login", wait_until="networkidle")
    page.wait_for_timeout(300)
    if page.locator('input[name="login"]').count() == 0:
        # already in portal or redirected
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
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)


def main() -> int:
    parser = argparse.ArgumentParser(description="Mobile audit for Fitness CRM")
    parser.add_argument("--base", default=DEFAULT_BASE, help="Base URL")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    OUT.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=2,
            has_touch=True,
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                "Mobile/15E148 Safari/604.1"
            ),
        )
        page = context.new_page()

        public_pages = [
            ("landing", "/"),
            ("docs", "/docs"),
            ("staff-login", f"/t/{SLUG}/login"),
            ("club", f"/club/{SLUG}/"),
            ("portal-login", f"/t/{SLUG}/portal/"),  # login form is on /portal/ itself
        ]
        for name, path in public_pages:
            _audit_page(page, base=base, path=path, name=name, results=results)

        try:
            _staff_login(page, base)
            for name, path in [
                ("dashboard", f"/t/{SLUG}/"),
                ("reception", f"/t/{SLUG}/reception/"),
            ]:
                _audit_page(page, base=base, path=path, name=name, results=results)
        except Exception as exc:
            results.append(
                {
                    "name": "staff-session",
                    "ok": False,
                    "error": f"staff login failed: {exc}",
                    "horizontal_overflow": False,
                }
            )
            print(f"[FAIL] staff-session: {exc}")

        portal = context.new_page()
        try:
            _portal_login(portal, base)
            _audit_page(
                portal,
                base=base,
                path=f"/t/{SLUG}/portal/",
                name="portal-home",
                results=results,
            )
        except Exception as exc:
            results.append(
                {
                    "name": "portal-home",
                    "ok": False,
                    "error": f"portal login/audit failed: {exc}",
                    "horizontal_overflow": False,
                }
            )
            print(f"[FAIL] portal-home: {exc}")

        browser.close()

    failed = [r for r in results if not r.get("ok")]
    report = {
        "base": base,
        "viewport": VIEWPORT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pass": len(results) - len(failed),
        "fail": len(failed),
        "results": results,
    }
    report_path = OUT / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport: {report_path}  PASS={report['pass']} FAIL={report['fail']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
