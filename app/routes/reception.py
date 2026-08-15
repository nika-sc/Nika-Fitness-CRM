"""Reception desk: search + card check-in."""
from datetime import date, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from app import limiter
from app.services.checkin_service import CheckinService
from app.services.feature_flags_service import FeatureFlagsService
from app.services.guest_service import GuestService
from app.services.member_service import MemberService
from app.services.membership_service import MembershipService
from app.services.portal_service import PortalService
from app.utils.decorators import feature_required, permission_required
from app.utils.periods import PERIODS, parse_date, period_bounds

bp = Blueprint('reception', __name__)


def _previous_bounds(start: date, end: date) -> tuple[date, date]:
    duration = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=duration - 1)
    return prev_start, prev_end


def _desk_deltas(attendance: dict, expiring_n: int) -> dict:
    today = date.today()
    yest = today - timedelta(days=1)
    prev = CheckinService.stats_for_range(yest, yest)
    exp_y = MembershipService.expiring_count_on(yest)
    return {
        'checkins': CheckinService.delta_pair(attendance['checkins'], prev['checkins']),
        'unique': CheckinService.delta_pair(attendance['unique_members'], prev['unique_members']),
        'expiring': CheckinService.delta_pair(expiring_n, exp_y),
    }


@bp.route('/')
@login_required
@permission_required('checkin')
def desk():
    from app.services.ops_service import ZoneService

    q = request.args.get('q', '').strip()
    visits_filter = 'present' if request.args.get('visits') == 'present' else 'all'
    members = MemberService.search_public(q, limit=20) if q else []
    expiring = MembershipService.expiring_members()[:5]
    expiring_n = MembershipService.expiring_count_on(date.today())
    attendance = CheckinService.today_stats()
    present = CheckinService.present_now()
    visits_today = CheckinService.today_visits(present_only=(visits_filter == 'present'))
    plans = MembershipService.list_plans(active_only=True)
    zones = []
    if FeatureFlagsService.is_enabled('module_zones'):
        try:
            zones = ZoneService.list_zones()
        except Exception:
            zones = []
    last_checkin = session.pop('desk_last', None)
    return render_template(
        'reception/desk.html',
        q=q,
        members=members,
        expiring=expiring,
        zones=zones,
        attendance=attendance,
        present=present,
        visits_today=visits_today,
        visits_filter=visits_filter,
        plans=plans,
        last_checkin=last_checkin,
        deltas=_desk_deltas(attendance, expiring_n),
        vip_numbers=MemberService.available_vip_numbers(),
        expiring_n=expiring_n,
        host_candidates=MemberService.list_members(limit=200),
    )


@bp.route('/trainer-slots', methods=['GET', 'POST'])
@login_required
@feature_required('module_trainer_slots')
@permission_required('manage_trainer_slots')
def trainer_slots():
    from app.services.trainer_slot_service import TrainerSlotService

    if request.method == 'POST':
        try:
            TrainerSlotService.book(
                int(request.form.get('slot_id')),
                int(request.form.get('member_id')),
                source='staff',
            )
            flash('Клиент записан к тренеру', 'success')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('reception.trainer_slots'))

    slots = TrainerSlotService.list_open(days=2)
    today = date.today()
    return render_template(
        'reception/trainer_slots.html',
        today_slots=[s for s in slots if s['starts_at'].date() == today],
        tomorrow_slots=[s for s in slots if s['starts_at'].date() == today + timedelta(days=1)],
        members=MemberService.list_members(limit=200),
    )


@bp.route('/stats')
@login_required
@permission_required('checkin')
def stats():
    period = (request.args.get('period') or 'today').strip()
    allowed = {p[0] for p in PERIODS}
    if period not in allowed:
        period = 'today'
    date_from = parse_date(request.args.get('date_from'))
    date_to = parse_date(request.args.get('date_to'))
    start, end = period_bounds(period, date_from, date_to)
    prev_start, prev_end = _previous_bounds(start, end)
    current = CheckinService.stats_for_range(start, end)
    previous = CheckinService.stats_for_range(prev_start, prev_end)
    today = date.today()
    present_n = len(CheckinService.present_now()) if start <= today <= end else None
    expiring_n = MembershipService.expiring_count_on(end)
    expiring_prev = MembershipService.expiring_count_on(prev_end)
    focus = (request.args.get('focus') or '').strip()
    return render_template(
        'reception/stats.html',
        periods=PERIODS,
        period=period,
        date_from=start.isoformat(),
        date_to=end.isoformat(),
        prev_from=prev_start.isoformat(),
        prev_to=prev_end.isoformat(),
        current=current,
        previous=previous,
        present_n=present_n,
        expiring_n=expiring_n,
        deltas={
            'checkins': CheckinService.delta_pair(current['checkins'], previous['checkins']),
            'unique': CheckinService.delta_pair(current['unique_members'], previous['unique_members']),
            'expiring': CheckinService.delta_pair(expiring_n, expiring_prev),
        },
        focus=focus,
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
        member = result['member']
        membership = result.get('membership') or {}
        visits = membership.get('visits_remaining')
        if visits is not None and visits > 0:
            visits = visits - 1
        ends_on = membership.get('ends_on')
        session['desk_last'] = {
            'name': member.get('full_name'),
            'member_id': member.get('id'),
            'card': member.get('card_number'),
            'message': result['message'],
            'level': level,
            'plan': membership.get('plan_name'),
            'ends_on': ends_on.isoformat() if hasattr(ends_on, 'isoformat') else (str(ends_on) if ends_on else None),
            'visits': visits,
        }
        msg = f"{member['full_name']}: {result['message']}"
        flash(
            msg,
            'error'
            if level == 'expired'
            else (
                'warning'
                if level == 'expiring'
                else ('info' if result.get('already_present') else 'success')
            ),
        )
        return redirect(url_for('members.detail', member_id=member['id'], checkin=1))
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('reception.desk'))


@bp.route('/api/search')
@login_required
@permission_required('checkin')
@limiter.limit('60 per minute')
def api_search():
    q = request.args.get('q', '')
    return jsonify({'members': MemberService.search_public(q, limit=15)})


@bp.route('/register', methods=['POST'])
@login_required
@permission_required('manage_members')
def register():
    try:
        name = (request.form.get('full_name') or '').strip()
        phone = (request.form.get('phone') or '').strip()
        if not name or not phone:
            raise ValueError('Укажите ФИО и телефон')
        vip = (request.form.get('vip_number') or '').strip()
        card = MemberService.validate_vip_number(vip) if vip else None
        member = MemberService.create({
            'full_name': name,
            'phone': phone,
            'email': (request.form.get('email') or '').strip(),
            'card_number': card,
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
    visits = (request.form.get('visits') or '').strip()
    target = (
        url_for('reception.desk', visits='present')
        if visits == 'present'
        else url_for('reception.desk')
    )
    return redirect(target + '#desk-visits')


@bp.route('/guest', methods=['POST'])
@login_required
@permission_required('checkin')
def guest():
    try:
        host_raw = (request.form.get('host_member_id') or '').strip()
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
