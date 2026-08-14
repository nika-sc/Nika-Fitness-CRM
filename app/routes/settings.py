"""Settings: users + email reminders trigger."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.services.feature_flags_service import FeatureFlagsService
from app.services.reminder_service import ReminderService
from app.services.user_service import UserService
from app.utils.decorators import permission_required

bp = Blueprint('settings', __name__)


@bp.route('/')
@login_required
@permission_required('manage_settings')
def index():
    kiosk_url = None
    try:
        from app.services.growth_service import KioskService
        device = KioskService.ensure_device()
        kiosk_url = url_for('kiosk.desk', token=device['token'])
    except Exception:
        kiosk_url = None
    return render_template(
        'settings/index.html',
        users=UserService.list_users(),
        modules=FeatureFlagsService.list_for_settings(),
        kiosk_url=kiosk_url,
    )


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
            actor_role=getattr(current_user, 'role', None),
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


@bp.route('/reminders/classes', methods=['POST'])
@login_required
@permission_required('manage_settings')
def class_reminders():
    try:
        sent = ReminderService.send_class_push()
        flash(f'Напоминаний о занятиях: {sent}', 'success')
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('settings.index'))


@bp.route('/modules', methods=['POST'])
@login_required
@permission_required('manage_settings')
def save_modules():
    FeatureFlagsService.save_from_form(request.form)
    flash('Модули клуба сохранены', 'success')
    return redirect(url_for('settings.index'))
