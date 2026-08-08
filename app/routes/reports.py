"""Reports."""
from flask import Blueprint, render_template
from flask_login import login_required

from app.services.report_service import ReportService
from app.utils.decorators import permission_required

bp = Blueprint('reports', __name__)


@bp.route('/')
@login_required
@permission_required('view_reports')
def index():
    summary = ReportService.summary()
    payments = ReportService.payments_period(30)
    return render_template('reports/index.html', summary=summary, payments=payments)
