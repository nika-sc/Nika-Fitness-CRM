"""Settings: users + email reminders trigger."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.services.reminder_service import ReminderService
from app.services.user_service import UserService
from app.utils.decorators import permission_required

bp = Blueprint('settings', __name__)


@bp.route('/')
@login_required
@permission_required('manage_settings')
def index():
    return render_template('settings/index.html', users=UserService.list_users())


@bp.route('/users', methods=['POST'])
@login_required
@permission_required('manage_users')
def create_user():
    try:
        UserService.create_user(
            username=request.form.get('username', '').strip(),
            password=request.form.get('password', ''),
            full_name=request.form.get('full_name', '').strip(),
            role=request.form.get('role', 'reception'),
        )
        flash('Пользователь создан', 'success')
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('settings.index'))


@bp.route('/reminders/run', methods=['POST'])
@login_required
@permission_required('manage_settings')
def run_reminders():
    try:
        sent = ReminderService.send_expiring_emails()
        flash(f'Отправлено напоминаний: {sent}', 'success')
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('settings.index'))
