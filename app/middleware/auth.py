"""Flask-Login user adapter (tenant-aware)."""
import logging

from flask import g, redirect, request, session, url_for
from flask_login import LoginManager, UserMixin

from app.database.connection import saas_enabled
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


class User(UserMixin):
    def __init__(self, user_dict):
        self.id = user_dict['id']
        self.username = user_dict['username']
        self.full_name = user_dict.get('full_name') or user_dict['username']
        self.role = user_dict.get('role', 'reception')
        self._is_active = bool(user_dict.get('is_active', True))
        self.tenant_slug = getattr(g, 'tenant_slug', None) or session.get('tenant_slug')

    @property
    def is_active(self):
        return self._is_active

    def get_id(self):
        # Encode tenant into session id to avoid cross-tenant collisions
        slug = self.tenant_slug or 'legacy'
        return f'{slug}:{self.id}'


def setup_auth(login_manager: LoginManager):
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Войдите в систему для доступа.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        try:
            if saas_enabled():
                from app.database.connection import get_tenant_dsn

                try:
                    get_tenant_dsn()
                except RuntimeError:
                    return None
            slug = None
            raw_id = user_id
            if isinstance(user_id, str) and ':' in user_id:
                slug, raw_id = user_id.split(':', 1)
            current_slug = getattr(g, 'tenant_slug', None) or session.get('tenant_slug')
            if saas_enabled() and slug and current_slug and slug != current_slug:
                return None
            user_dict = UserService.get_user_by_id(int(raw_id))
            if user_dict:
                return User(user_dict)
        except Exception as exc:
            logger.error('user_loader error: %s', exc)
        return None

    @login_manager.unauthorized_handler
    def unauthorized():
        slug = getattr(g, 'tenant_slug', None)
        if slug and slug != 'legacy':
            return redirect(url_for('auth.login', slug=slug, next=request.path))
        if saas_enabled():
            return redirect(url_for('public.index'))
        return redirect(url_for('auth.login', next=request.path))
