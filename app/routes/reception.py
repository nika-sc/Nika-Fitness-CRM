"""Reception desk: search + card check-in + guest visits."""
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.services.checkin_service import CheckinService
from app.services.feature_flags_service import FeatureFlagsService
from app.services.guest_service import GuestService
from app.services.member_service import MemberService
from app.services.membership_service import MembershipService
from app.services.portal_service import PortalService
from app.utils.decorators import permission_required

bp = Blueprint('reception', __name__)


@bp.route('/')
@login_required
@permission_required('checkin')
def desk():
    from app.services.ops_service import ZoneService

    q = request.args.get('q', '').strip()
    members = MemberService.list_members(q=q, limit=20) if q else []
    recent = CheckinService.recent(20)
    expiring = MembershipService.expiring_members()[:5]
    guests_today = GuestService.list_today()
    host_candidates = MemberService.list_members(limit=200)
    attendance = CheckinService.today_stats()
    present = CheckinService.present_now()
    plans = MembershipService.list_plans(active_only=True)
    zones = []
    if FeatureFlagsService.is_enabled('module_zones'):
        try:
            zones = ZoneService.list_zones()
        except Exception:
            zones = []
    return render_template(
        'reception/desk.html',
        q=q,
        members=members,
        recent=recent,
        expiring=expiring,
        guests_today=guests_today,
        host_candidates=host_candidates,
        zones=zones,
        attendance=attendance,
        present=present,
        plans=plans,
    )


@bp.route('/checkin', methods=['POST'])
@login_required
@permission_required('checkin')
def checkin():
    card = (request.form.get('card_number') or '').strip()
    member_id = request.form.get('member_id')
    zone = (request.form.get('zone') or '').strip() or None
    try:
        if member_id:
            result = CheckinService.check_in(
                int(member_id), created_by=current_user.id, zone_code=zone
            )
        elif card:
            result = CheckinService.check_in_by_card(
                card, created_by=current_user.id, zone_code=zone
            )
        else:
            flash('Укажите номер карты или клиента', 'error')
            return redirect(url_for('reception.desk'))
        level = result['alert_level']
        msg = f"{result['member']['full_name']}: {result['message']}"
        flash(msg, 'error' if level == 'expired' else ('warning' if level == 'expiring' else 'success'))
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('reception.desk'))


@bp.route('/guest', methods=['POST'])
@login_required
@permission_required('checkin')
def guest():
    host_raw = (request.form.get('host_member_id') or '').strip()
    try:
        GuestService.create(
            guest_name=request.form.get('guest_name') or '',
            guest_phone=request.form.get('guest_phone') or '',
            host_member_id=int(host_raw) if host_raw else None,
            amount=request.form.get('amount') or 0,
            method=request.form.get('method') or 'cash',
            note=request.form.get('note') or '',
            created_by=current_user.id,
        )
        flash('Гостевой визит записан', 'success')
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('reception.desk'))


@bp.route('/api/search')
@login_required
@permission_required('checkin')
def api_search():
    q = request.args.get('q', '')
    members = MemberService.list_members(q=q, limit=15)
    return jsonify({'members': members})


@bp.route('/register', methods=['POST'])
@login_required
@permission_required('manage_members')
def register():
    try:
        name = (request.form.get('full_name') or '').strip()
        phone = (request.form.get('phone') or '').strip()
        if not name or not phone:
            raise ValueError('Укажите ФИО и телефон')
        member = MemberService.create({
            'full_name': name,
            'phone': phone,
            'email': (request.form.get('email') or '').strip(),
        })
        plan_raw = (request.form.get('plan_id') or '').strip()
        if plan_raw:
            MembershipService.sell(
                member['id'],
                int(plan_raw),
                request.form.get('method') or 'cash',
                current_user.id,
                note='Ресепшен: новый клиент',
            )
        password = (request.form.get('portal_password') or '').strip()
        if password or request.form.get('issue_portal'):
            PortalService.set_password(member['id'], password or None, send_email=False)
        flash(f'Клиент {member["full_name"]} создан, карта {member["card_number"]}', 'success')
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('reception.desk'))


@bp.route('/checkout', methods=['POST'])
@login_required
@permission_required('checkin')
def checkout():
    try:
        CheckinService.checkout(int(request.form.get('checkin_id')))
        flash('Выход отмечен', 'success')
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('reception.desk'))
