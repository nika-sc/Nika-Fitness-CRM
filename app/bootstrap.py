"""Blueprint registration helpers for self-hosted and SaaS editions."""
from __future__ import annotations

from flask import Flask, g

from app.database.connection import get_legacy_database_url, set_tenant_context


def _feature_blueprints():
    from app.routes import features as feat
    return [
        (feat.portal_bp, '/portal'),
        (feat.pt_bp, '/pt'),
        (feat.messaging_bp, '/messaging'),
        (feat.zones_bp, '/zones'),
        (feat.corporate_bp, '/corporate'),
        (feat.cash_bp, '/cash'),
        (feat.lockers_bp, '/lockers'),
        (feat.loyalty_bp, '/loyalty'),
        (feat.leads_bp, '/leads'),
        (feat.branches_bp, '/branches'),
        (feat.payments_bp, '/payments-online'),
        (feat.spa_bp, '/spa'),
        (feat.kiosk_bp, '/kiosk'),
        (feat.nps_bp, '/nps'),
    ]


FEATURE_BLUEPRINTS = None  # lazy via get_feature_blueprints()


def get_feature_blueprints():
    global FEATURE_BLUEPRINTS
    if FEATURE_BLUEPRINTS is None:
        FEATURE_BLUEPRINTS = _feature_blueprints()
    return FEATURE_BLUEPRINTS


def _core_blueprints():
    from app.routes.alerts import bp as alerts_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.club_site import club_public_bp, site_admin_bp
    from app.routes.main import bp as main_bp
    from app.routes.members import bp as members_bp
    from app.routes.memberships import bp as memberships_bp
    from app.routes.reception import bp as reception_bp
    from app.routes.reports import bp as reports_bp
    from app.routes.schedule import bp as schedule_bp
    from app.routes.settings import bp as settings_bp
    from app.routes.trainers import bp as trainers_bp
    return {
        'auth': auth_bp,
        'main': main_bp,
        'members': members_bp,
        'memberships': memberships_bp,
        'reception': reception_bp,
        'schedule': schedule_bp,
        'trainers': trainers_bp,
        'alerts': alerts_bp,
        'reports': reports_bp,
        'settings': settings_bp,
        'site_admin': site_admin_bp,
        'club_public': club_public_bp,
    }


def init_single_tenant(app: Flask) -> None:
    """Register blueprints without /t/<slug> and bind legacy DATABASE_URL."""

    @app.before_request
    def _legacy_tenant_context():
        if getattr(g, '_tenant_tokens', None):
            return None
        g.tenant = None
        g.tenant_slug = 'legacy'
        g._tenant_tokens = set_tenant_context('legacy', get_legacy_database_url())
        return None

    @app.teardown_request
    def _clear_legacy_tenant(_exc=None):
        tokens = getattr(g, '_tenant_tokens', None)
        if tokens:
            from app.database.connection import reset_tenant_context
            reset_tenant_context(tokens)
            g._tenant_tokens = None

    bps = _core_blueprints()
    app.register_blueprint(bps['auth'])
    app.register_blueprint(bps['main'])
    app.register_blueprint(bps['members'], url_prefix='/members')
    app.register_blueprint(bps['memberships'], url_prefix='/memberships')
    app.register_blueprint(bps['reception'], url_prefix='/reception')
    app.register_blueprint(bps['schedule'], url_prefix='/schedule')
    app.register_blueprint(bps['trainers'], url_prefix='/trainers')
    app.register_blueprint(bps['alerts'], url_prefix='/alerts')
    app.register_blueprint(bps['reports'], url_prefix='/reports')
    app.register_blueprint(bps['settings'], url_prefix='/settings')
    app.register_blueprint(bps['site_admin'], url_prefix='/site-admin')
    app.register_blueprint(bps['club_public'], url_prefix='/club')
    for bp, path in get_feature_blueprints():
        app.register_blueprint(bp, url_prefix=path)


def register_tenant_blueprints(app: Flask, feature_bps=None) -> None:
    """Register club blueprints under /t/<slug>/… (SaaS)."""
    bps = _core_blueprints()
    prefix = '/t/<slug>'
    app.register_blueprint(bps['auth'], url_prefix=prefix)
    app.register_blueprint(bps['main'], url_prefix=prefix)
    app.register_blueprint(bps['members'], url_prefix=f'{prefix}/members')
    app.register_blueprint(bps['memberships'], url_prefix=f'{prefix}/memberships')
    app.register_blueprint(bps['reception'], url_prefix=f'{prefix}/reception')
    app.register_blueprint(bps['schedule'], url_prefix=f'{prefix}/schedule')
    app.register_blueprint(bps['trainers'], url_prefix=f'{prefix}/trainers')
    app.register_blueprint(bps['alerts'], url_prefix=f'{prefix}/alerts')
    app.register_blueprint(bps['reports'], url_prefix=f'{prefix}/reports')
    app.register_blueprint(bps['settings'], url_prefix=f'{prefix}/settings')
    app.register_blueprint(bps['site_admin'], url_prefix=f'{prefix}/site-admin')
    app.register_blueprint(bps['club_public'], url_prefix='/club/<slug>')
    for bp, path in (feature_bps or get_feature_blueprints()):
        app.register_blueprint(bp, url_prefix=f'{prefix}{path}')
