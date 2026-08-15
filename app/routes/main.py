"""Dashboard."""
from flask import Blueprint, Response, current_app, redirect, render_template, url_for
import json
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
    if current_user.role == 'trainer':
        from app.services.trainer_service import TrainerService
        if TrainerService.by_user(current_user.id):
            return redirect(url_for('trainer_cabinet.week'))
    summary = ReportService.summary()
    alerts = AlertService.list_recent(12)
    recent = CheckinService.recent(10)
    return render_template(
        'dashboard.html',
        summary=summary,
        alerts=alerts,
        recent=recent,
    )


@bp.route('/manifest.webmanifest')
@login_required
def staff_manifest():
    start = url_for('reception.desk') if current_user.role == 'reception' else url_for('main.dashboard')
    body = {
        'name': 'Nika Fit',
        'short_name': 'Nika Fit',
        'description': 'Стойка, клиенты и касса клуба',
        'start_url': start,
        'scope': url_for('main.index'),
        'display': 'standalone',
        'background_color': '#0b1220',
        'theme_color': '#ff5a3c',
        'icons': [
            {
                'src': url_for('static', filename='icons/nf-pwa.svg'),
                'sizes': 'any',
                'type': 'image/svg+xml',
                'purpose': 'any maskable',
            }
        ],
    }
    return Response(json.dumps(body, ensure_ascii=False), mimetype='application/manifest+json')


@bp.route('/sw.js')
@login_required
def staff_sw():
    response = current_app.send_static_file('js/staff-sw.js')
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    return response
