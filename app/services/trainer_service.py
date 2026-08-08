"""Trainers catalog."""
from __future__ import annotations

from app.database.connection import execute, execute_returning, fetch_all, fetch_one


class TrainerService:
    @staticmethod
    def list_all(active_only: bool = False) -> list[dict]:
        if active_only:
            return fetch_all('SELECT * FROM trainers WHERE is_active = TRUE ORDER BY full_name')
        return fetch_all('SELECT * FROM trainers ORDER BY full_name')

    @staticmethod
    def get(trainer_id: int) -> dict | None:
        return fetch_one('SELECT * FROM trainers WHERE id = %s', (trainer_id,))

    @staticmethod
    def create(data: dict) -> dict:
        return execute_returning(
            """
            INSERT INTO trainers (full_name, phone, email, bio, photo_path, is_active)
            VALUES (%s, %s, %s, %s, %s, TRUE)
            RETURNING *
            """,
            (
                data['full_name'].strip(),
                (data.get('phone') or '').strip(),
                (data.get('email') or '').strip(),
                (data.get('bio') or '').strip(),
                data.get('photo_path'),
            ),
        )

    @staticmethod
    def update(trainer_id: int, data: dict) -> dict | None:
        return execute_returning(
            """
            UPDATE trainers SET
                full_name = %s,
                phone = %s,
                email = %s,
                bio = %s,
                photo_path = COALESCE(%s, photo_path),
                is_active = %s
            WHERE id = %s
            RETURNING *
            """,
            (
                data['full_name'].strip(),
                (data.get('phone') or '').strip(),
                (data.get('email') or '').strip(),
                (data.get('bio') or '').strip(),
                data.get('photo_path'),
                data.get('is_active', True),
                trainer_id,
            ),
        )

    @staticmethod
    def delete(trainer_id: int) -> int:
        return execute('DELETE FROM trainers WHERE id = %s', (trainer_id,))
