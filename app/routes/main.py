"""Dashboard."""
from flask import Blueprint, redirect, render_template, url_for
from flask_login import login_required, current_user

from app.services.alert_service import AlertService
from app.services.checkin_service import CheckinService
from app.services.report_service import ReportService

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@bp.route('/dashboard')
@login_required
def dashboard():
    # Reception works from the desk; owner/admin stay on the overview dashboard.
    if current_user.role == 'reception':
        return redirect(url_for('reception.desk'))
    summary = ReportService.summary()
    alerts = AlertService.list_recent(12)
    recent = CheckinService.recent(10)
    return render_template(
        'dashboard.html',
        summary=summary,
        alerts=alerts,
        recent=recent,
    )
