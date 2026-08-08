"""Group schedule."""
from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.services.member_service import MemberService
from app.services.schedule_service import ScheduleService
from app.services.trainer_service import TrainerService
from app.services.user_service import UserService
from app.utils.decorators import permission_required

bp = Blueprint('schedule', __name__)


def _week_start_from_args():
    raw = request.args.get('week')
    if raw:
        try:
            d = datetime.fromisoformat(raw)
            return d.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=d.weekday())
        except ValueError:
            pass
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return today - timedelta(days=today.weekday())


@bp.route('/')
@login_required
@permission_required('view_schedule')
def week():
    week_start = _week_start_from_args()
    sessions = ScheduleService.list_sessions(week_start)
    return render_template(
        'schedule/week.html',
        sessions=sessions,
        week_start=week_start,
        prev_week=(week_start - timedelta(days=7)).date().isoformat(),
        next_week=(week_start + timedelta(days=7)).date().isoformat(),
        class_types=ScheduleService.list_types(),
        trainers=TrainerService.list_all(active_only=True),
    )


@bp.route('/sessions/new', methods=['POST'])
@login_required
@permission_required('manage_schedule')
def create_session():
    try:
        ScheduleService.create_session({
            'class_type_id': request.form.get('class_type_id'),
            'trainer_id': request.form.get('trainer_id'),
            'room_name': request.form.get('room_name'),
            'starts_at': request.form.get('starts_at'),
            'ends_at': request.form.get('ends_at'),
            'capacity': request.form.get('capacity'),
            'price': request.form.get('price'),
            'notes': request.form.get('notes'),
        })
        flash('Занятие добавлено', 'success')
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('schedule.week', week=request.args.get('week')))


@bp.route('/sessions/<int:session_id>', methods=['GET', 'POST'])
@login_required
@permission_required('view_schedule')
def session_detail(session_id):
    session = ScheduleService.get_session(session_id)
    if not session:
        flash('Занятие не найдено', 'error')
        return redirect(url_for('schedule.week'))
    if request.method == 'POST':
        action = (request.form.get('action') or 'book').strip()
        try:
            if action == 'book':
                if not UserService.check_permission(current_user.id, 'manage_schedule'):
                    flash('Недостаточно прав', 'error')
                else:
                    member_id = int(request.form.get('member_id'))
                    ScheduleService.book(session_id, member_id, source='staff')
                    flash('Клиент записан', 'success')
            elif action == 'noshow':
                if not UserService.check_permission(current_user.id, 'manage_schedule'):
                    flash('Недостаточно прав', 'error')
                else:
                    result = ScheduleService.mark_noshows(session_id)
                    flash(
                        f"Неявки: {result['marked']}, списано визитов: {result['deducted']}",
                        'success' if result['marked'] else 'info',
                    )
            elif action == 'attended':
                if not UserService.check_permission(current_user.id, 'manage_schedule'):
                    flash('Недостаточно прав', 'error')
                else:
                    booking_id = int(request.form.get('booking_id'))
                    ScheduleService.mark_attended(booking_id)
                    flash('Отмечено присутствие', 'success')
            elif action == 'cancel':
                if not UserService.check_permission(current_user.id, 'manage_schedule'):
                    flash('Недостаточно прав', 'error')
                else:
                    from app.services.waitlist_service import WaitlistService
                    ScheduleService.cancel_booking(int(request.form.get('booking_id')))
                    promoted = WaitlistService.promote_next(session_id)
                    if promoted:
                        flash(f"Запись отменена; с waitlist записан {promoted.get('full_name')}", 'success')
                    else:
                        flash('Запись отменена', 'info')
            elif action == 'waitlist':
                if not UserService.check_permission(current_user.id, 'manage_waitlist'):
                    flash('Недостаточно прав', 'error')
                else:
                    from app.services.waitlist_service import WaitlistService
                    WaitlistService.join(session_id, int(request.form.get('member_id')))
                    flash('Добавлен в лист ожидания', 'success')
            elif action == 'promote':
                if not UserService.check_permission(current_user.id, 'manage_waitlist'):
                    flash('Недостаточно прав', 'error')
                else:
                    from app.services.waitlist_service import WaitlistService
                    row = WaitlistService.promote_next(session_id)
                    flash(
                        f"Записан с waitlist: {row['full_name']}" if row else 'Лист ожидания пуст',
                        'success' if row else 'info',
                    )
            else:
                flash('Неизвестное действие', 'error')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('schedule.session_detail', session_id=session_id))
    from app.services.waitlist_service import WaitlistService
    bookings = ScheduleService.session_bookings(session_id)
    members = MemberService.list_members(limit=200)
    waitlist = WaitlistService.list_for_session(session_id)
    return render_template(
        'schedule/session.html',
        session=session,
        bookings=bookings,
        members=members,
        waitlist=waitlist,
    )


@bp.route('/types', methods=['GET', 'POST'])
@login_required
@permission_required('manage_schedule')
def types():
    if request.method == 'POST':
        try:
            ScheduleService.create_type({
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'price': request.form.get('price') or 0,
                'capacity': request.form.get('capacity') or 15,
            })
            flash('Тип занятия добавлен', 'success')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('schedule.types'))
    return render_template('schedule/types.html', types=ScheduleService.list_types(active_only=False))
