"""Auth decorators."""
from functools import wraps

from flask import flash, jsonify, redirect, request, url_for
from flask_login import current_user, login_required

from app.services.user_service import UserService


def permission_required(permission: str):
    def decorator(f):
        @wraps(f)
        @login_required
        def wrapped(*args, **kwargs):
            is_api = '/api/' in request.path
            if not current_user.is_authenticated:
                if is_api:
                    return jsonify({'success': False, 'error': 'auth_required'}), 401
                flash('Войдите в систему.', 'error')
                return redirect(url_for('auth.login'))
            if not UserService.check_permission(current_user.id, permission):
                if is_api:
                    return jsonify({'success': False, 'error': 'forbidden'}), 403
                flash('Недостаточно прав.', 'error')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return wrapped
    return decorator
