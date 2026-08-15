"""Trainer cabinet: own slots, bookings and attendance marks."""
from datetime import date, datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.services.trainer_service import TrainerService
from app.services.trainer_slot_service import TrainerSlotService
from app.utils.decorators import feature_required, permission_required

bp = Blueprint('trainer_cabinet', __name__)

DAY_NAMES = ('Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье')


def _week_start_from_args() -> date:
    raw = request.args.get('week')
    if raw:
        try:
            parsed = date.fromisoformat(raw)
            return parsed - timedelta(days=parsed.weekday())
        except ValueError:
            pass
    today = date.today()
    return today - timedelta(days=today.weekday())


def _my_trainer() -> dict | None:
    return TrainerService.by_user(current_user.id)


def _own_slot(trainer: dict, slot_id: int) -> dict:
    slot = TrainerSlotService.get(slot_id)
    if not slot or int(slot['trainer_id']) != int(trainer['id']):
        raise ValueError('Слот не найден')
    return slot


@bp.route('/')
@login_required
@feature_required('module_trainer_slots')
@permission_required('manage_trainer_slots')
def week():
    trainer = _my_trainer()
    if not trainer:
        return render_template('trainer/not_linked.html')

    week_start = _week_start_from_args()
    week_end = week_start + timedelta(days=6)
    slots = TrainerSlotService.list_for_trainer(trainer['id'], week_start, week_end)
    today = date.today()

    by_day: dict = {}
    for slot in slots:
        by_day.setdefault(slot['starts_at'].date(), []).append(slot)
    week_days = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        week_days.append({
            'date': day,
            'name': DAY_NAMES[i],
            'is_today': day == today,
            'slots': by_day.get(day, []),
        })

    return render_template(
        'trainer/week.html',
        trainer=trainer,
        week_days=week_days,
        week_start=week_start,
        prev_week=(week_start - timedelta(days=7)).isoformat(),
        next_week=(week_start + timedelta(days=7)).isoformat(),
        today_iso=today.isoformat(),
        default_date=max(today, week_start).isoformat(),
        stats=TrainerSlotService.stats_for_trainer(trainer['id']),
        upcoming=TrainerSlotService.list_for_trainer(trainer['id'], today, today + timedelta(days=60)),
    )


@bp.route('/slots', methods=['POST'])
@login_required
@feature_required('module_trainer_slots')
@permission_required('manage_trainer_slots')
def create_slots():
    trainer = _my_trainer()
    if not trainer:
        return render_template('trainer/not_linked.html')
    try:
        created = TrainerSlotService.create(
            trainer_id=trainer['id'],
            slot_date=request.form.get('slot_date') or '',
            start_time=request.form.get('start_time') or '',
            duration_min=int(request.form.get('duration_min') or 60),
            repeat_weekdays=request.form.getlist('weekday'),
            repeat_until=request.form.get('repeat_until'),
            place=request.form.get('place') or '',
            created_by=current_user.id,
        )
        flash(f'Открыто окон: {len(created)}', 'success')
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('trainer_cabinet.week', week=request.form.get('week')))


@bp.route('/slots/<int:slot_id>', methods=['POST'])
@login_required
@feature_required('module_trainer_slots')
@permission_required('manage_trainer_slots')
def slot_action(slot_id):
    trainer = _my_trainer()
    if not trainer:
        return render_template('trainer/not_linked.html')
    action = (request.form.get('action') or '').strip()
    try:
        _own_slot(trainer, slot_id)
        if action == 'confirm':
            TrainerSlotService.confirm(slot_id)
            flash('Запись подтверждена, клиент увидит это в личном кабинете', 'success')
        elif action == 'decline':
            TrainerSlotService.decline(slot_id, reason=request.form.get('reason') or '')
            flash('Заявка отклонена, окно снова свободно', 'info')
        elif action == 'done':
            TrainerSlotService.mark(slot_id, 'done')
            flash('Отмечено: тренировка проведена', 'success')
        elif action == 'no_show':
            TrainerSlotService.mark(slot_id, 'no_show')
            flash('Отмечено: клиент не пришёл', 'info')
        elif action == 'release':
            TrainerSlotService.cancel_booking(slot_id)
            flash('Запись отменена, слот снова свободен', 'info')
        elif action == 'close':
            TrainerSlotService.close(slot_id)
            flash('Окно снято', 'info')
        else:
            flash('Неизвестное действие', 'error')
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('trainer_cabinet.week', week=request.form.get('week')))
