"""Login / logout (tenant-scoped)."""
from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for
from flask_login import login_user, logout_user, current_user

from app.middleware.auth import User
from app.services.user_service import UserService

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    club_name = None
    if getattr(g, 'tenant', None):
        club_name = g.tenant.get('name')
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        client_key = f"{request.remote_addr}:{getattr(g, 'tenant_slug', '')}:{username.lower()}"
        user, err = UserService.authenticate(username, password, client_key, current_app.config)
        if err:
            flash(err, 'error')
            return render_template('auth/login.html', club_name=club_name), 401
        session['tenant_slug'] = getattr(g, 'tenant_slug', None) or 'legacy'
        login_user(User(user), remember=False)
        nxt = request.args.get('next')
        if nxt and nxt.startswith('/'):
            return redirect(nxt)
        return redirect(url_for('main.dashboard'))
    return render_template('auth/login.html', club_name=club_name)


@bp.route('/logout')
def logout():
    logout_user()
    session.pop('tenant_slug', None)
    flash('Вы вышли из системы.', 'info')
    slug = getattr(g, 'tenant_slug', None)
    if slug and slug != 'legacy':
        return redirect(url_for('auth.login', slug=slug))
    return redirect(url_for('public.index'))
