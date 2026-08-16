"""Nika Fitness CRM application factory."""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime

from flask import Flask, g, request, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import Config, ProductionConfig
from app.database.connection import saas_enabled
from app.utils.security import DEFAULT_SECRET_KEY, TALISMAN_CSP, security_headers

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

    env_name = (os.environ.get('FLASK_ENV') or '').strip().lower()
    is_prod = env_name == 'production' or config_class is ProductionConfig or (
        isinstance(config_class, type) and issubclass(config_class, ProductionConfig)
    )
    secret = os.environ.get('SECRET_KEY') or app.config.get('SECRET_KEY') or ''
    if is_prod and secret in ('', DEFAULT_SECRET_KEY):
        raise RuntimeError('SECRET_KEY must be set to a non-default value in production')
    if os.environ.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    if os.environ.get('RATELIMIT_STORAGE_URI'):
        app.config['RATELIMIT_STORAGE_URI'] = os.environ.get('RATELIMIT_STORAGE_URI')

    if not app.debug:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    csrf.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    storage_uri = (app.config.get('RATELIMIT_STORAGE_URI') or 'memory://').strip()
    if storage_uri.startswith('redis'):
        try:
            import redis as redis_lib
            redis_lib.Redis.from_url(storage_uri).ping()
        except Exception:
            logging.getLogger(__name__).warning(
                'Rate-limit storage %s unavailable, falling back to memory://',
                storage_uri,
            )
            storage_uri = 'memory://'
            app.config['RATELIMIT_STORAGE_URI'] = storage_uri
    limiter.init_app(app)

    from flask_talisman import Talisman

    Talisman(
        app,
        force_https=False,
        strict_transport_security=bool(is_prod and not app.debug),
        strict_transport_security_max_age=31536000,
        content_security_policy=TALISMAN_CSP,
        referrer_policy='strict-origin-when-cross-origin',
        frame_options='SAMEORIGIN',
        session_cookie_secure=False,
        session_cookie_http_only=True,
    )

    from app.utils.session_lifetime import MidnightSessionInterface

    app.session_interface = MidnightSessionInterface()

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

    @app.before_request
    def _secure_session_cookie():
        proto = (request.headers.get('X-Forwarded-Proto') or '').split(',')[0].strip().lower()
        app.config['SESSION_COOKIE_SECURE'] = proto == 'https' or request.is_secure
        return None

    @app.before_request
    def _expire_staff_at_midnight():
        until = session.get('staff_until')
        if not until:
            return None
        try:
            ts = float(until)
        except (TypeError, ValueError):
            return None
        if time.time() < ts:
            return None
        from flask_login import logout_user

        logout_user()
        session.pop('staff_until', None)
        session.permanent = False
        return None

    @app.after_request
    def _security_headers(response):
        for key, value in security_headers(request.path or '').items():
            response.headers.setdefault(key, value)
        return response

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
        my_trainer_card = None
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
            try:
                from app.services.trainer_service import TrainerService
                my_trainer_card = TrainerService.by_user(current_user.id)
            except Exception:
                my_trainer_card = None
        from app.utils.labels import method_label, role_label, source_label, status_label, status_pill_class

        return {
            'has_permission': has_permission,
            'feature_enabled': feature_enabled,
            'role_label': role_label,
            'status_label': status_label,
            'method_label': method_label,
            'source_label': source_label,
            'status_pill_class': status_pill_class,
            'unread_alerts': unread,
            'my_trainer_card': my_trainer_card,
            'club_name': club_name,
            'tenant_slug': tenant_slug,
            'saas_mode': saas_enabled(),
            'demo_mode': bool(app.config.get('DEMO_MODE')),
            'demo_credentials': {
                'staff_user': app.config.get('DEMO_STAFF_USER', ''),
                'staff_password': app.config.get('DEMO_STAFF_PASSWORD', ''),
                'portal_login': app.config.get('DEMO_PORTAL_LOGIN', ''),
                'portal_password': app.config.get('DEMO_PORTAL_PASSWORD', ''),
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
