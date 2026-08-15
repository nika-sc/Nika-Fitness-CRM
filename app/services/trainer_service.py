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
    def by_user(user_id: int) -> dict | None:
        return fetch_one('SELECT * FROM trainers WHERE user_id = %s', (user_id,))

    @staticmethod
    def link_candidates() -> list[dict]:
        """Staff accounts that can be attached to a trainer card."""
        return fetch_all(
            """
            SELECT u.id, u.username, u.full_name, u.role, t.id AS linked_trainer_id
            FROM users u
            LEFT JOIN trainers t ON t.user_id = u.id
            WHERE u.is_active = TRUE AND u.role = 'trainer'
            ORDER BY u.full_name, u.username
            """
        )

    @staticmethod
    def create(data: dict) -> dict:
        return execute_returning(
            """
            INSERT INTO trainers (full_name, phone, email, bio, photo_path, user_id, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            RETURNING *
            """,
            (
                data['full_name'].strip(),
                (data.get('phone') or '').strip(),
                (data.get('email') or '').strip(),
                (data.get('bio') or '').strip(),
                data.get('photo_path'),
                TrainerService._clean_user_id(data.get('user_id')),
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
                user_id = %s,
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
                TrainerService._clean_user_id(data.get('user_id'), trainer_id),
                data.get('is_active', True),
                trainer_id,
            ),
        )

    @staticmethod
    def _clean_user_id(raw, trainer_id: int | None = None) -> int | None:
        value = str(raw or '').strip()
        if not value:
            return None
        try:
            user_id = int(value)
        except ValueError:
            raise ValueError('Некорректная учётная запись')
        user = fetch_one("SELECT id FROM users WHERE id = %s AND role = 'trainer'", (user_id,))
        if not user:
            raise ValueError('Учётная запись должна быть сотрудником с ролью «Тренер»')
        taken = fetch_one(
            'SELECT id FROM trainers WHERE user_id = %s AND (%s IS NULL OR id <> %s)',
            (user_id, trainer_id, trainer_id),
        )
        if taken:
            raise ValueError('Эта учётная запись уже привязана к другому тренеру')
        return user_id

    @staticmethod
    def delete(trainer_id: int) -> int:
        return execute('DELETE FROM trainers WHERE id = %s', (trainer_id,))
