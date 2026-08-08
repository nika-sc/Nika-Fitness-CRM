"""Email notifications via Flask-Mail."""
from __future__ import annotations

import logging

from flask import current_app
from flask_mail import Message

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def send_email(to: str, subject: str, body: str) -> bool:
        if not to:
            return False
        try:
            from app import mail
            msg = Message(
                subject=subject,
                recipients=[to],
                body=body,
                sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
            )
            mail.send(msg)
            return True
        except Exception as exc:
            logger.warning('Email send failed to=%s: %s', to, exc)
            return False

    @staticmethod
    def membership_expiring(member: dict, membership: dict, days_left: int) -> bool:
        subject = f"Абонемент скоро заканчивается — карта {member.get('card_number')}"
        body = (
            f"Здравствуйте, {member.get('full_name')}!\n\n"
            f"Ваш абонемент действует до {membership.get('ends_on')}. "
            f"Осталось примерно {days_left} дн.\n"
            f"Номер карты: {member.get('card_number')}\n\n"
            f"Пожалуйста, продлите абонемент в клубе Nika Fitness.\n"
        )
        return NotificationService.send_email(member.get('email') or '', subject, body)
