"""Login / logout (tenant-scoped)."""
from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for
from flask_login import login_user, logout_user, current_user

from app import limiter
from app.middleware.auth import User
from app.services.user_service import UserService
from app.utils.security import rotate_session, safe_next_url
from app.utils.session_lifetime import next_midnight_timestamp

bp = Blueprint('auth', __name__)


def perform_staff_login(username: str, password: str, remember: bool):
    """Authenticate staff inside the already resolved tenant context.

    Returns an error message, or None when the session is established.
    Callers must have g.tenant_slug set for the club being entered.
    """
    tenant_slug = getattr(g, 'tenant_slug', None) or 'legacy'
    client_key = f"{request.remote_addr}:{tenant_slug}:{username.lower()}"
    user, err = UserService.authenticate(
        username, password, client_key, current_app.config, ip=request.remote_addr or '',
    )
    if err:
        return err
    rotate_session()
    session['tenant_slug'] = tenant_slug
    if remember:
        session.permanent = True
        session['staff_until'] = next_midnight_timestamp(
            current_app.config.get('TIMEZONE_OFFSET', 3)
        )
    login_user(User(user), remember=False)
    return None


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute', methods=['POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    club_name = None
    if getattr(g, 'tenant', None):
        club_name = g.tenant.get('name')
    if request.method == 'POST':
        err = perform_staff_login(
            (request.form.get('username') or '').strip(),
            request.form.get('password') or '',
            bool(request.form.get('remember')),
        )
        if err:
            flash(err, 'error')
            return render_template('auth/login.html', club_name=club_name), 401
        nxt = safe_next_url(request.args.get('next'), url_for('main.dashboard'))
        return redirect(nxt)
    return render_template('auth/login.html', club_name=club_name)


@bp.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'GET':
        if current_user.is_authenticated:
            return render_template('auth/logout_confirm.html')
        slug = getattr(g, 'tenant_slug', None)
        if slug and slug != 'legacy':
            return redirect(url_for('auth.login', slug=slug))
        return redirect(url_for('public.index'))
    logout_user()
    session.pop('tenant_slug', None)
    session.pop('staff_until', None)
    session.pop('portal_member_id', None)
    session.pop('portal_login', None)
    flash('Вы вышли из системы.', 'info')
    slug = getattr(g, 'tenant_slug', None)
    if slug and slug != 'legacy':
        return redirect(url_for('auth.login', slug=slug))
    return redirect(url_for('public.index'))
