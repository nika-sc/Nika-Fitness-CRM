"""Members CRUD."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.services.checkin_service import CheckinService
from app.services.member_service import MemberService
from app.services.membership_service import MembershipService
from app.services.settings_service import SettingsService
from app.utils.decorators import permission_required
from app.utils.uploads import save_image

bp = Blueprint('members', __name__)


@bp.route('/')
@login_required
@permission_required('view_members')
def list_members():
    q = request.args.get('q')
    members = MemberService.list_members(q=q)
    return render_template('members/list.html', members=members, q=q or '')


@bp.route('/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_members')
def create():
    if request.method == 'POST':
        try:
            photo_path = None
            if request.files.get('photo') and request.files['photo'].filename:
                photo_path = save_image(request.files['photo'], 'members')
            member = MemberService.create({
                'full_name': request.form.get('full_name', ''),
                'phone': request.form.get('phone', ''),
                'email': request.form.get('email', ''),
                'notes': request.form.get('notes', ''),
                'photo_path': photo_path,
            })
            flash(f"Клиент создан. Карта: {member['card_number']}", 'success')
            return redirect(url_for('members.detail', member_id=member['id']))
        except Exception as exc:
            flash(str(exc), 'error')
    return render_template('members/form.html', member=None)


@bp.route('/<int:member_id>')
@login_required
@permission_required('view_members')
def detail(member_id):
    member = MemberService.get(member_id)
    if not member:
        flash('Клиент не найден', 'error')
        return redirect(url_for('members.list_members'))
    memberships = MembershipService.list_for_member(member_id)
    payments = MembershipService.list_payments(member_id=member_id)
    checkins = CheckinService.for_member(member_id)
    current = MembershipService.current_for_member(member_id)
    plans = MembershipService.list_plans()
    active_freeze = None
    freeze_days_used = 0
    freeze_max_days = 30
    if current:
        active_freeze = MembershipService.active_freeze(current['id'])
        freeze_days_used = MembershipService.freeze_days_used_this_year(current['id'])
        freeze_max_days = SettingsService.get_int('freeze_max_days_per_year', 30)
    from app.services.growth_service import MedicalService
    from app.services.crm_extra_service import LoyaltyService
    from app.services.pt_service import PtService
    medical = MedicalService.latest(member_id)
    loyalty = LoyaltyService.get_account(member_id)
    pt_packages = PtService.list_packages(member_id)
    if request.args.get('add_cert') == '1' and request.method == 'GET':
        pass
    return render_template(
        'members/detail.html',
        member=member,
        memberships=memberships,
        payments=payments,
        checkins=checkins,
        current=current,
        plans=plans,
        active_freeze=active_freeze,
        freeze_days_used=freeze_days_used,
        freeze_max_days=freeze_max_days,
        medical=medical,
        loyalty=loyalty,
        pt_packages=pt_packages,
    )


@bp.route('/<int:member_id>/qr.png')
@login_required
@permission_required('view_members')
def qr_png(member_id):
    member = MemberService.get(member_id)
    if not member:
        flash('Клиент не найден', 'error')
        return redirect(url_for('members.list_members'))
    from app.routes.features import render_member_qr_png
    return render_member_qr_png(member['card_number'])


@bp.route('/<int:member_id>/medical', methods=['POST'])
@login_required
@permission_required('manage_members')
def add_medical(member_id):
    from app.services.growth_service import MedicalService
    try:
        MedicalService.add(
            member_id,
            expires_on=request.form.get('expires_on') or '',
            issued_on=request.form.get('issued_on') or None,
            note=request.form.get('note') or '',
        )
        flash('Медсправка сохранена', 'success')
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('members.detail', member_id=member_id))


@bp.route('/<int:member_id>/portal-password', methods=['POST'])
@login_required
@permission_required('manage_members')
def portal_password(member_id):
    from app.services.portal_service import PortalService

    member = MemberService.get(member_id)
    if not member:
        flash('Клиент не найден', 'error')
        return redirect(url_for('members.list_members'))
    action = request.form.get('action') or 'generate'
    try:
        if action == 'set':
            plain = PortalService.set_password(
                member_id,
                password=request.form.get('password') or '',
                send_email=True,
            )
            flash(f'Пароль ЛК сохранён: {plain}', 'success')
        else:
            plain = PortalService.set_password(member_id, password=None, send_email=True)
            flash(f'Пароль ЛК сгенерирован: {plain} (также в outbox / на email)', 'success')
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('members.detail', member_id=member_id))


@bp.route('/<int:member_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_members')
def edit(member_id):
    member = MemberService.get(member_id)
    if not member:
        flash('Клиент не найден', 'error')
        return redirect(url_for('members.list_members'))
    if request.method == 'POST':
        try:
            photo_path = None
            if request.files.get('photo') and request.files['photo'].filename:
                photo_path = save_image(request.files['photo'], 'members')
            MemberService.update(member_id, {
                'full_name': request.form.get('full_name', ''),
                'phone': request.form.get('phone', ''),
                'email': request.form.get('email', ''),
                'notes': request.form.get('notes', ''),
                'status': request.form.get('status', 'active'),
                'photo_path': photo_path,
            })
            flash('Сохранено', 'success')
            return redirect(url_for('members.detail', member_id=member_id))
        except Exception as exc:
            flash(str(exc), 'error')
    return render_template('members/form.html', member=member)
