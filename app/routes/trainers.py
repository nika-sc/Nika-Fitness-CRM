"""Trainers."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.services.trainer_service import TrainerService
from app.utils.decorators import permission_required
from app.utils.uploads import save_image

bp = Blueprint('trainers', __name__)


@bp.route('/')
@login_required
@permission_required('view_trainers')
def list_trainers():
    return render_template('trainers/list.html', trainers=TrainerService.list_all())


@bp.route('/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_trainers')
def create():
    if request.method == 'POST':
        try:
            photo_path = None
            if request.files.get('photo') and request.files['photo'].filename:
                photo_path = save_image(request.files['photo'], 'trainers')
            trainer = TrainerService.create({
                'full_name': request.form.get('full_name', ''),
                'phone': request.form.get('phone', ''),
                'email': request.form.get('email', ''),
                'bio': request.form.get('bio', ''),
                'photo_path': photo_path,
            })
            flash('Тренер добавлен', 'success')
            return redirect(url_for('trainers.detail', trainer_id=trainer['id']))
        except Exception as exc:
            flash(str(exc), 'error')
    return render_template('trainers/form.html', trainer=None)


@bp.route('/<int:trainer_id>')
@login_required
@permission_required('view_trainers')
def detail(trainer_id):
    trainer = TrainerService.get(trainer_id)
    if not trainer:
        flash('Тренер не найден', 'error')
        return redirect(url_for('trainers.list_trainers'))
    return render_template('trainers/detail.html', trainer=trainer)


@bp.route('/<int:trainer_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_trainers')
def edit(trainer_id):
    trainer = TrainerService.get(trainer_id)
    if not trainer:
        flash('Тренер не найден', 'error')
        return redirect(url_for('trainers.list_trainers'))
    if request.method == 'POST':
        try:
            photo_path = None
            if request.files.get('photo') and request.files['photo'].filename:
                photo_path = save_image(request.files['photo'], 'trainers')
            TrainerService.update(trainer_id, {
                'full_name': request.form.get('full_name', ''),
                'phone': request.form.get('phone', ''),
                'email': request.form.get('email', ''),
                'bio': request.form.get('bio', ''),
                'is_active': request.form.get('is_active') == 'on',
                'photo_path': photo_path,
            })
            flash('Сохранено', 'success')
            return redirect(url_for('trainers.detail', trainer_id=trainer_id))
        except Exception as exc:
            flash(str(exc), 'error')
    return render_template('trainers/form.html', trainer=trainer)
