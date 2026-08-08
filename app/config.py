"""Конфигурация Nika Fitness CRM."""
import os
from datetime import timedelta

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    # selfhosted | saas — saas requires the app.saas package (stripped from public edition)
    APP_EDITION = (os.environ.get('APP_EDITION') or 'selfhosted').strip().lower()
    DB_DRIVER = 'postgres'
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    PLATFORM_DATABASE_URL = os.environ.get('PLATFORM_DATABASE_URL', '')
    TENANT_DB_ADMIN_URL = os.environ.get('TENANT_DB_ADMIN_URL', '')
    TENANT_DATABASE_URL_TEMPLATE = os.environ.get('TENANT_DATABASE_URL_TEMPLATE', '')
    TENANT_BASE_DOMAIN = os.environ.get('TENANT_BASE_DOMAIN', '')
    PLATFORM_ADMIN_USER = os.environ.get('PLATFORM_ADMIN_USER', '')
    PLATFORM_ADMIN_PASSWORD = os.environ.get('PLATFORM_ADMIN_PASSWORD', '')
    DEMO_MODE = os.environ.get('DEMO_MODE', 'False').lower() == 'true'
    DEMO_STAFF_USER = os.environ.get('DEMO_STAFF_USER', 'admin')
    DEMO_STAFF_PASSWORD = os.environ.get('DEMO_STAFF_PASSWORD', 'admin123')
    DEMO_PORTAL_LOGIN = os.environ.get('DEMO_PORTAL_LOGIN', 'smelkov2008@yandex.ru')
    DEMO_PORTAL_PASSWORD = os.environ.get('DEMO_PORTAL_PASSWORD', 'client123')

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    SESSION_COOKIE_NAME = os.environ.get('SESSION_COOKIE_NAME', 'nikafit_session')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', str(8 * 1024 * 1024)))
    TRUSTED_HOSTS = [
        h.strip().lower()
        for h in (os.environ.get('TRUSTED_HOSTS', 'localhost,127.0.0.1') or '').split(',')
        if h.strip()
    ]

    WRITE_API_RATE_LIMIT_PER_MIN = int(os.environ.get('WRITE_API_RATE_LIMIT_PER_MIN', '120'))
    LOGIN_LOCKOUT_THRESHOLD = int(os.environ.get('LOGIN_LOCKOUT_THRESHOLD', '8'))
    LOGIN_LOCKOUT_WINDOW_SEC = int(os.environ.get('LOGIN_LOCKOUT_WINDOW_SEC', '600'))
    LOGIN_LOCKOUT_DURATION_SEC = int(os.environ.get('LOGIN_LOCKOUT_DURATION_SEC', '900'))

    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')
    RATELIMIT_DEFAULT = '3000 per day;1000 per hour'
    ITEMS_PER_PAGE = 50
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    TIMEZONE_OFFSET = int(os.environ.get('TIMEZONE_OFFSET', '3'))

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@nika-fitness.local')
    MAIL_TIMEOUT = int(os.environ.get('MAIL_TIMEOUT', 5))

    MEMBERSHIP_EXPIRING_DAYS = int(os.environ.get('MEMBERSHIP_EXPIRING_DAYS', '7'))
    UPLOAD_FOLDER = os.path.join(_PROJECT_ROOT, 'static', 'uploads')
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    DEMO_MODE = False
    SESSION_COOKIE_SECURE = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
