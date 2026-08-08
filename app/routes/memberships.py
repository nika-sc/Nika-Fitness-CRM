"""Plans, sell membership, payments list."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.services.membership_service import MembershipService
from app.utils.decorators import permission_required

bp = Blueprint('memberships', __name__)


@bp.route('/plans', methods=['GET', 'POST'])
@login_required
@permission_required('manage_memberships')
def plans():
    if request.method == 'POST':
        try:
            MembershipService.create_plan({
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'duration_days': request.form.get('duration_days'),
                'visit_limit': request.form.get('visit_limit') or None,
                'price': request.form.get('price') or 0,
            })
            flash('План добавлен', 'success')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('memberships.plans'))
    return render_template('memberships/plans.html', plans=MembershipService.list_plans(active_only=False))


@bp.route('/sell/<int:member_id>', methods=['POST'])
@login_required
@permission_required('manage_memberships')
def sell(member_id):
    try:
        MembershipService.sell(
            member_id=member_id,
            plan_id=int(request.form.get('plan_id')),
            method=request.form.get('method') or 'cash',
            created_by=current_user.id,
            note=request.form.get('note') or '',
        )
        flash('Абонемент оформлен и оплата записана', 'success')
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('members.detail', member_id=member_id))


@bp.route('/payments')
@login_required
@permission_required('view_memberships')
def payments():
    rows = MembershipService.list_payments()
    return render_template('memberships/payments.html', payments=rows)


@bp.route('/<int:membership_id>/freeze', methods=['POST'])
@login_required
@permission_required('manage_memberships')
def freeze(membership_id):
    membership = MembershipService.get_membership(membership_id)
    if not membership:
        flash('Абонемент не найден', 'error')
        return redirect(url_for('members.list_members'))
    try:
        MembershipService.freeze(
            membership_id,
            reason=request.form.get('reason') or '',
            created_by=current_user.id,
        )
        flash('Абонемент заморожен', 'success')
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('members.detail', member_id=membership['member_id']))


@bp.route('/<int:membership_id>/unfreeze', methods=['POST'])
@login_required
@permission_required('manage_memberships')
def unfreeze(membership_id):
    membership = MembershipService.get_membership(membership_id)
    if not membership:
        flash('Абонемент не найден', 'error')
        return redirect(url_for('members.list_members'))
    try:
        updated = MembershipService.unfreeze(membership_id)
        days = updated.get('freeze_days_added', 0)
        flash(f'Абонемент разморожен, срок продлён на {days} дн.', 'success')
    except Exception as exc:
        flash(str(exc), 'error')
    return redirect(url_for('members.detail', member_id=membership['member_id']))
