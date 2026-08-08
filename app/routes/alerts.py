"""Staff alerts feed."""
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required

from app.services.alert_service import AlertService
from app.utils.decorators import permission_required

bp = Blueprint('alerts', __name__)


@bp.route('/')
@login_required
@permission_required('view_alerts')
def list_alerts():
    return render_template('alerts/list.html', alerts=AlertService.list_recent(100))


@bp.route('/read-all', methods=['POST'])
@login_required
@permission_required('view_alerts')
def read_all():
    AlertService.mark_all_read()
    flash('Все алерты отмечены прочитанными', 'success')
    return redirect(url_for('alerts.list_alerts'))
