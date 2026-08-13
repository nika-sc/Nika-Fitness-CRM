"""Nika Fitness CRM application factory."""
from __future__ import annotations

import logging
import os
from datetime import datetime

from flask import Flask, g, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import Config
from app.database.connection import saas_enabled

csrf = CSRFProtect()
login_manager = LoginManager()
mail = Mail()
limiter = Limiter(key_func=get_remote_address, default_limits=[])


def create_app(config_class=Config):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(
        __name__,
        template_folder=os.path.join(project_root, 'templates'),
        static_folder=os.path.join(project_root, 'static'),
    )
    app.config.from_object(config_class)
    # Re-read edition from env so tests / reload can switch without reimporting Config
    app.config['APP_EDITION'] = (os.environ.get('APP_EDITION') or 'selfhosted').strip().lower()
    app.extensions.setdefault('saas_landing', None)

    if not app.debug:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    csrf.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    from app.middleware.auth import setup_auth
    setup_auth(login_manager)

    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'members'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'trainers'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'club'), exist_ok=True)

    @app.before_request
    def _trusted_hosts():
        hosts = app.config.get('TRUSTED_HOSTS') or []
        if not hosts or app.debug:
            return None
        host = (request.host or '').split(':')[0].lower()
        if host and host not in hosts:
            return ('Invalid Host header', 400)
        return None

    @app.context_processor
    def inject_globals():
        from app.services.user_service import UserService
        from app.services.alert_service import AlertService
        from app.database.connection import fetch_one

        def has_permission(name: str) -> bool:
            if not current_user.is_authenticated:
                return False
            return UserService.check_permission(current_user.id, name)

        def feature_enabled(name: str) -> bool:
            from app.services.feature_flags_service import FeatureFlagsService
            try:
                return FeatureFlagsService.is_enabled(name)
            except Exception:
                return False

        unread = 0
        club_name = 'Nika Fitness'
        tenant_slug = getattr(g, 'tenant_slug', None)
        if getattr(g, 'tenant', None):
            club_name = g.tenant.get('name') or club_name
        if current_user.is_authenticated:
            try:
                unread = AlertService.unread_count()
            except Exception:
                unread = 0
            try:
                row = fetch_one("SELECT value FROM app_settings WHERE key = 'club_name'")
                if row and row.get('value'):
                    club_name = row['value']
            except Exception:
                pass
        return {
            'has_permission': has_permission,
            'feature_enabled': feature_enabled,
            'unread_alerts': unread,
            'club_name': club_name,
            'tenant_slug': tenant_slug,
            'saas_mode': saas_enabled(),
            'demo_mode': bool(app.config.get('DEMO_MODE')),
            'demo_credentials': {
                'staff_user': app.config.get('DEMO_STAFF_USER', ''),
                'staff_password': app.config.get('DEMO_STAFF_PASSWORD', ''),
                'portal_login': app.config.get('DEMO_PORTAL_LOGIN', ''),
                'portal_password': app.config.get('DEMO_PORTAL_PASSWORD', ''),
                'platform_user': app.config.get('PLATFORM_ADMIN_USER', ''),
                'platform_password': app.config.get('PLATFORM_ADMIN_PASSWORD', ''),
            } if app.config.get('DEMO_MODE') else {},
            'now': datetime.now(),
        }

    from app.routes.public import bp as public_bp
    app.register_blueprint(public_bp)

    edition = (app.config.get('APP_EDITION') or 'selfhosted').strip().lower()
    init_saas = None
    if edition == 'saas':
        try:
            from app.saas import init_saas as _init_saas
            init_saas = _init_saas
        except ModuleNotFoundError:
            init_saas = None

    if init_saas and edition == 'saas':
        init_saas(app)
    else:
        from app.bootstrap import init_single_tenant
        init_single_tenant(app)

    logging.basicConfig(level=logging.INFO)
    return app
