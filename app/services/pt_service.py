"""PT packages and sessions."""
from __future__ import annotations

from datetime import datetime, timedelta

from app.database.connection import execute, execute_returning, fetch_all, fetch_one


class PtService:
    @staticmethod
    def list_packages(member_id: int | None = None) -> list[dict]:
        if member_id:
            return fetch_all(
                """
                SELECT p.*, t.full_name AS trainer_name, m.full_name AS member_name
                FROM pt_packages p
                LEFT JOIN trainers t ON t.id = p.trainer_id
                JOIN members m ON m.id = p.member_id
                WHERE p.member_id = %s ORDER BY p.id DESC
                """,
                (member_id,),
            )
        return fetch_all(
            """
            SELECT p.*, t.full_name AS trainer_name, m.full_name AS member_name
            FROM pt_packages p
            LEFT JOIN trainers t ON t.id = p.trainer_id
            JOIN members m ON m.id = p.member_id
            ORDER BY p.id DESC LIMIT 200
            """
        )

    @staticmethod
    def sell(member_id: int, trainer_id: int | None, title: str, sessions: int, price: float, days: int = 90) -> dict:
        total = int(sessions)
        price_cents = int(round(float(price or 0) * 100))
        expires = (datetime.now() + timedelta(days=int(days))).date()
        pkg = execute_returning(
            """
            INSERT INTO pt_packages (member_id, trainer_id, title, sessions_total, sessions_left, price_cents, expires_on)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *
            """,
            (member_id, trainer_id or None, title or 'PT пакет', total, total, price_cents, expires),
        )
        if price_cents > 0:
            from app.services.ops_service import CashService

            execute_returning(
                """
                INSERT INTO payments (member_id, amount_cents, method, note, cash_shift_id)
                VALUES (%s, %s, 'card', %s, %s) RETURNING id
                """,
                (member_id, price_cents, f"PT: {pkg['title']}", CashService.open_shift_id()),
            )
        return pkg

    @staticmethod
    def schedule_session(package_id: int, starts_at: str, note: str = '') -> dict:
        pkg = fetch_one('SELECT * FROM pt_packages WHERE id = %s', (package_id,))
        if not pkg or pkg['status'] != 'active':
            raise ValueError('Пакет не найден или неактивен')
        if pkg['sessions_left'] <= 0:
            raise ValueError('Нет оставшихся сессий')
        starts = datetime.fromisoformat(starts_at)
        ends = starts + timedelta(hours=1)
        sess = execute_returning(
            """
            INSERT INTO pt_sessions (package_id, trainer_id, member_id, starts_at, ends_at, status, note)
            VALUES (%s, %s, %s, %s, %s, 'scheduled', %s) RETURNING *
            """,
            (package_id, pkg.get('trainer_id'), pkg['member_id'], starts, ends, note or ''),
        )
        return sess

    @staticmethod
    def complete_session(session_id: int) -> dict:
        sess = fetch_one('SELECT * FROM pt_sessions WHERE id = %s', (session_id,))
        if not sess:
            raise ValueError('Сессия не найдена')
        execute("UPDATE pt_sessions SET status = 'done' WHERE id = %s", (session_id,))
        execute(
            """
            UPDATE pt_packages SET sessions_left = GREATEST(0, sessions_left - 1),
              status = CASE WHEN sessions_left - 1 <= 0 THEN 'exhausted' ELSE status END
            WHERE id = %s
            """,
            (sess['package_id'],),
        )
        return fetch_one('SELECT * FROM pt_sessions WHERE id = %s', (session_id,))

    @staticmethod
    def list_sessions(limit: int = 100) -> list[dict]:
        return fetch_all(
            """
            SELECT s.*, m.full_name AS member_name, t.full_name AS trainer_name, p.title AS package_title
            FROM pt_sessions s
            JOIN members m ON m.id = s.member_id
            LEFT JOIN trainers t ON t.id = s.trainer_id
            JOIN pt_packages p ON p.id = s.package_id
            ORDER BY s.starts_at DESC LIMIT %s
            """,
            (limit,),
        )

    @staticmethod
    def commission_report(days: int = 30) -> list[dict]:
        return fetch_all(
            """
            SELECT t.id, t.full_name,
                   COUNT(s.id)::int AS sessions_done,
                   COALESCE(r.percent, 40)::float AS percent,
                   COALESCE(SUM(p.price_cents / NULLIF(p.sessions_total, 0)), 0)::bigint AS session_value_cents
            FROM pt_sessions s
            JOIN trainers t ON t.id = s.trainer_id
            JOIN pt_packages p ON p.id = s.package_id
            LEFT JOIN trainer_commission_rules r ON r.trainer_id = t.id AND r.is_active
            WHERE s.status = 'done' AND s.starts_at >= NOW() - (%s || ' days')::interval
            GROUP BY t.id, t.full_name, r.percent
            ORDER BY sessions_done DESC
            """,
            (str(days),),
        )
