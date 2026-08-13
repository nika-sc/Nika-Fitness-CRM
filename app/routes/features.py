"""Phase 2–6 feature routes (staff + public portal/nps/kiosk)."""
from __future__ import annotations

import io
import json

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required

from app import csrf
from app.services.crm_extra_service import LeadService, LoyaltyService, NpsService, SegmentService
from app.services.club_site_service import ClubSiteService
from app.services.growth_service import (
    BranchService,
    KioskService,
    MedicalService,
    PaymentIntentService,
    PushService,
    SpaService,
)
from app.services.member_service import MemberService
from app.services.membership_service import MembershipService
from app.services.message_service import MessageService
from app.services.ops_service import CashService, CorporateService, LockerService, ZoneService
from app.services.member_portal_service import MemberPortalService
from app.services.portal_service import PortalService
from app.services.pt_service import PtService
from app.services.schedule_service import ScheduleService
from app.services.trainer_service import TrainerService
from app.services.user_service import UserService
from app.services.waitlist_service import WaitlistService
from app.utils.decorators import feature_required, permission_required

portal_bp = Blueprint('portal', __name__)
pt_bp = Blueprint('pt', __name__)
messaging_bp = Blueprint('messaging', __name__)
zones_bp = Blueprint('zones', __name__)
corporate_bp = Blueprint('corporate', __name__)
cash_bp = Blueprint('cash', __name__)
lockers_bp = Blueprint('lockers', __name__)
loyalty_bp = Blueprint('loyalty', __name__)
leads_bp = Blueprint('leads', __name__)
branches_bp = Blueprint('branches', __name__)
payments_bp = Blueprint('payments_online', __name__)
spa_bp = Blueprint('spa', __name__)
kiosk_bp = Blueprint('kiosk', __name__)
nps_bp = Blueprint('nps', __name__)


# ----- Portal (public member LK) -----
@portal_bp.route('/', methods=['GET', 'POST'])
def home():
    member = PortalService.current_member()
    if request.method == 'POST':
        action = request.form.get('action')
        try:
            if action == 'login':
                PortalService.login(
                    request.form.get('login') or '',
                    request.form.get('password') or '',
                )
                flash('Вход выполнен', 'success')
                return redirect(url_for('portal.home'))
            elif action == 'logout':
                PortalService.logout()
                return redirect(url_for('portal.home'))
            elif action == 'book':
                booking = PortalService.book(int(request.form.get('session_id')))
                name = booking.get('class_name') or 'занятие'
                flash(f'Вы записаны: {name}. Запись подтверждена.', 'success')
            elif action == 'cancel':
                PortalService.cancel(int(request.form.get('booking_id')))
                flash('Запись отменена', 'info')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('portal.home'))

    site = ClubSiteService.get()
    dash = MemberPortalService.dashboard(member['id']) if member else None
    return render_template(
        'portal/home.html',
        member=member,
        dash=dash,
        membership=dash['active_membership'] if dash else None,
        site=site,
        theme=ClubSiteService.theme(site),
    )


@portal_bp.route('/qr.png')
def qr_png():
    """QR with card number for reception check-in (portal session only)."""
    member = PortalService.current_member()
    if not member:
        abort(401)
    return render_member_qr_png(member['card_number'])


@portal_bp.route('/manifest.webmanifest')
def manifest():
    body = {
        'name': 'Личный кабинет',
        'short_name': 'ЛК клуба',
        'description': 'Абонемент, QR-пропуск и запись на занятия',
        'start_url': url_for('portal.home'),
        'scope': url_for('portal.home'),
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


@portal_bp.route('/sw.js')
def service_worker():
    response = current_app.send_static_file('js/portal-sw.js')
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    return response


@portal_bp.route('/offline')
def offline():
    return render_template('portal/offline.html')


@portal_bp.route('/push-subscribe', methods=['POST'])
def push_subscribe():
    member = PortalService.current_member()
    if not member:
        abort(401)
    data = request.get_json(silent=True) or {}
    endpoint = (data.get('endpoint') or '').strip()
    if not endpoint:
        return jsonify({'ok': False, 'error': 'endpoint required'}), 400
    PushService.subscribe(member['id'], endpoint, json.dumps(data.get('keys') or {}, ensure_ascii=False))
    return jsonify({'ok': True})


# ----- PT -----
@pt_bp.route('/', methods=['GET', 'POST'])
@login_required
@feature_required('module_pt')
@permission_required('manage_pt')
def index():
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            if action == 'sell':
                PtService.sell(
                    member_id=int(request.form.get('member_id')),
                    trainer_id=int(request.form.get('trainer_id')) if request.form.get('trainer_id') else None,
                    title=request.form.get('title') or 'PT пакет',
                    sessions=int(request.form.get('sessions') or 10),
                    price=request.form.get('price') or 0,
                )
                flash('PT-пакет оформлен', 'success')
            elif action == 'schedule':
                PtService.schedule_session(
                    int(request.form.get('package_id')),
                    request.form.get('starts_at') or '',
                    request.form.get('note') or '',
                )
                flash('Сессия запланирована', 'success')
            elif action == 'complete':
                PtService.complete_session(int(request.form.get('session_id')))
                flash('Сессия списана', 'success')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('pt.index'))
    return render_template(
        'features/pt.html',
        packages=PtService.list_packages(),
        sessions=PtService.list_sessions(),
        members=MemberService.list_members(limit=200),
        trainers=TrainerService.list_all(active_only=True),
        commissions=PtService.commission_report(),
    )


# ----- Messaging -----
@messaging_bp.route('/')
@login_required
@feature_required('module_messaging')
@permission_required('manage_messaging')
def index():
    return render_template('features/messaging.html', messages=MessageService.list_recent())


@messaging_bp.route('/send', methods=['POST'])
@login_required
@feature_required('module_messaging')
@permission_required('manage_messaging')
def send():
    try:
        MessageService.send(
            request.form.get('channel') or 'sms',
            request.form.get('recipient') or '',
            request.form.get('template_key') or 'manual',
            {'text': request.form.get('text') or ''},
        )
        flash('Сообщение записано в outbox (stub)', 'success')
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('messaging.index'))


# ----- Zones -----
@zones_bp.route('/', methods=['GET', 'POST'])
@login_required
@feature_required('module_zones')
@permission_required('manage_zones')
def index():
    if request.method == 'POST':
        try:
            ZoneService.create(request.form.get('code') or '', request.form.get('name') or '')
            flash('Зона добавлена', 'success')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('zones.index'))
    return render_template('features/zones.html', zones=ZoneService.list_zones(False))


# ----- Corporate -----
@corporate_bp.route('/', methods=['GET', 'POST'])
@login_required
@feature_required('module_corporate')
@permission_required('manage_corporate')
def index():
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            if action == 'create':
                CorporateService.create({
                    'name': request.form.get('name'),
                    'contact_phone': request.form.get('contact_phone'),
                    'contact_email': request.form.get('contact_email'),
                    'seats_limit': request.form.get('seats_limit'),
                    'note': request.form.get('note'),
                })
                flash('Контракт создан', 'success')
            elif action == 'assign':
                CorporateService.assign_member(
                    int(request.form.get('member_id')),
                    int(request.form.get('corporate_id')) if request.form.get('corporate_id') else None,
                )
                flash('Клиент привязан', 'success')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('corporate.index'))
    return render_template(
        'features/corporate.html',
        accounts=CorporateService.list_all(),
        members=MemberService.list_members(limit=200),
    )


# ----- Cash -----
@cash_bp.route('/', methods=['GET', 'POST'])
@login_required
@permission_required('manage_cash')
def index():
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            if action == 'open':
                CashService.open_shift(current_user.id, int(float(request.form.get('opening') or 0) * 100))
                flash('Смена открыта', 'success')
            elif action == 'close':
                CashService.close_shift(current_user.id, int(float(request.form.get('closing') or 0) * 100))
                flash('Смена закрыта', 'success')
            elif action == 'debt':
                CashService.create_debt(
                    int(request.form.get('member_id')),
                    request.form.get('amount') or 0,
                    request.form.get('note') or '',
                    current_user.id,
                )
                flash('Долг создан', 'success')
            elif action == 'pay_debt':
                CashService.pay_debt(int(request.form.get('debt_id')), request.form.get('amount') or 0, current_user.id)
                flash('Оплата долга принята', 'success')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('cash.index'))
    return render_template(
        'features/cash.html',
        shift=CashService.current_shift(),
        shift_totals=CashService.payment_totals(shift_id=CashService.open_shift_id()) if CashService.current_shift() else None,
        today=CashService.payment_totals(today=True),
        shifts=CashService.list_shifts(),
        debts=CashService.list_debts(),
        members=MemberService.list_members(limit=200),
    )


# ----- Lockers -----
@lockers_bp.route('/', methods=['GET', 'POST'])
@login_required
@feature_required('module_lockers')
@permission_required('manage_lockers')
def index():
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            if action == 'create':
                LockerService.create(request.form.get('code') or '', request.form.get('zone') or 'main')
            elif action == 'assign':
                LockerService.assign(int(request.form.get('locker_id')), int(request.form.get('member_id')))
            elif action == 'release':
                LockerService.release(int(request.form.get('locker_id')))
            flash('Сохранено', 'success')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('lockers.index'))
    return render_template(
        'features/lockers.html',
        lockers=LockerService.list_all(),
        members=MemberService.list_members(limit=200),
    )


# ----- Loyalty / segments / NPS list -----
@loyalty_bp.route('/', methods=['GET', 'POST'])
@login_required
@feature_required('module_loyalty')
@permission_required('manage_loyalty')
def index():
    if request.method == 'POST':
        try:
            LoyaltyService.adjust(
                int(request.form.get('member_id')),
                int(request.form.get('delta') or 0),
                request.form.get('reason') or '',
                current_user.id,
            )
            flash('Баллы обновлены', 'success')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('loyalty.index'))
    segments = SegmentService.list_segments()
    selected = request.args.get('segment')
    segment_members = SegmentService.members_for_rule(selected) if selected else []
    return render_template(
        'features/loyalty.html',
        segments=segments,
        selected=selected,
        segment_members=segment_members,
        members=MemberService.list_members(limit=200),
        nps=NpsService.list_recent(50),
    )


# ----- Leads -----
@leads_bp.route('/', methods=['GET', 'POST'])
@login_required
@feature_required('module_leads')
@permission_required('manage_leads')
def index():
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            if action == 'create':
                LeadService.create({
                    'full_name': request.form.get('full_name'),
                    'phone': request.form.get('phone'),
                    'email': request.form.get('email'),
                    'source': request.form.get('source'),
                    'note': request.form.get('note'),
                    'assigned_to': request.form.get('assigned_to'),
                })
            elif action == 'status':
                LeadService.set_status(
                    int(request.form.get('lead_id')),
                    request.form.get('status') or 'new',
                    int(request.form.get('assigned_to')) if request.form.get('assigned_to') else None,
                )
            flash('Сохранено', 'success')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('leads.index'))
    return render_template(
        'features/leads.html',
        leads=LeadService.list_all(),
        users=UserService.list_users(),
    )


# ----- Branches -----
@branches_bp.route('/', methods=['GET', 'POST'])
@login_required
@feature_required('module_branches')
@permission_required('manage_branches')
def index():
    if request.method == 'POST':
        try:
            BranchService.create(
                request.form.get('code') or '',
                request.form.get('name') or '',
                request.form.get('address') or '',
            )
            flash('Филиал добавлен', 'success')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('branches.index'))
    return render_template('features/branches.html', branches=BranchService.list_all(False))


# ----- Online payments -----
@payments_bp.route('/', methods=['GET', 'POST'])
@login_required
@feature_required('module_payments_online')
@permission_required('manage_payments_online')
def index():
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            if action == 'create':
                PaymentIntentService.create(
                    int(request.form.get('member_id')) if request.form.get('member_id') else None,
                    request.form.get('amount') or 0,
                    request.form.get('purpose') or 'membership',
                    current_user.id,
                )
                flash('Intent создан (stub)', 'success')
            elif action == 'paid':
                PaymentIntentService.mark_paid(int(request.form.get('intent_id')))
                flash('Отмечено оплаченным', 'success')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('payments_online.index'))
    return render_template(
        'features/payments.html',
        intents=PaymentIntentService.list_recent(),
        members=MemberService.list_members(limit=200),
    )


@payments_bp.route('/webhook', methods=['POST'])
@csrf.exempt
@feature_required('module_payments_online')
def webhook():
    # Stub webhook: mark by external_id
    data = request.get_json(silent=True) or {}
    ext = data.get('external_id') or request.form.get('external_id')
    if not ext:
        return {'ok': False, 'error': 'external_id required'}, 400
    from app.database.connection import fetch_one
    row = fetch_one('SELECT id FROM payment_intents WHERE external_id = %s', (ext,))
    if not row:
        return {'ok': False, 'error': 'not found'}, 404
    PaymentIntentService.mark_paid(row['id'])
    return {'ok': True}


# ----- SPA / bar / kids -----
@spa_bp.route('/', methods=['GET', 'POST'])
@login_required
@feature_required('module_spa')
@permission_required('manage_spa')
def index():
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            if action == 'book':
                SpaService.book(
                    int(request.form.get('service_id')),
                    int(request.form.get('member_id')) if request.form.get('member_id') else None,
                    request.form.get('starts_at') or '',
                )
            elif action == 'bar':
                SpaService.bar_sale(
                    request.form.get('item_name') or 'Товар',
                    request.form.get('amount') or 0,
                    int(request.form.get('member_id')) if request.form.get('member_id') else None,
                    current_user.id,
                )
            elif action == 'kids':
                SpaService.kids_book(
                    int(request.form.get('parent_member_id')),
                    request.form.get('child_name') or '',
                    request.form.get('starts_at') or '',
                    request.form.get('ends_at') or '',
                )
            flash('Сохранено', 'success')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('spa.index'))
    return render_template(
        'features/spa.html',
        services=SpaService.list_services(),
        bookings=SpaService.list_bookings(),
        kids=SpaService.list_kids(),
        members=MemberService.list_members(limit=200),
    )


# ----- Kiosk -----
@kiosk_bp.route('/', methods=['GET', 'POST'])
def desk():
    from app.services.checkin_service import CheckinService

    device = KioskService.ensure_device()
    msg = None
    level = 'ok'
    if request.method == 'POST':
        try:
            card = (request.form.get('card_number') or '').strip()
            result = CheckinService.check_in_by_card(card, created_by=None)
            # override source conceptually — already card
            msg = f"{result['member']['full_name']}: {result['message']}"
            level = result['alert_level']
        except Exception as exc:
            msg = str(exc)
            level = 'expired'
    return render_template('features/kiosk.html', device=device, msg=msg, level=level)


# ----- NPS public -----
@nps_bp.route('/', methods=['GET', 'POST'])
def form():
    member_id = request.args.get('member') or request.form.get('member_id')
    if request.method == 'POST':
        try:
            NpsService.submit(
                int(member_id) if member_id else None,
                int(request.form.get('score') or 0),
                request.form.get('comment') or '',
            )
            flash('Спасибо за оценку!', 'success')
            return redirect(url_for('nps.form'))
        except Exception as exc:
            flash(str(exc), 'error')
    return render_template('features/nps.html', member_id=member_id)


# ----- Member QR helper used from members routes -----
def render_member_qr_png(card_number: str) -> Response:
    import qrcode

    img = qrcode.make(card_number)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='image/png')
