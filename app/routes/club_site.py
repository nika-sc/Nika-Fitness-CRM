"""Public club landing + staff site editor + booking requests from the site."""
from __future__ import annotations

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import limiter
from app.database.connection import saas_enabled
from app.services.club_site_service import (
    AMENITY_ICONS,
    MAX_AMENITIES,
    MAX_GALLERY_PHOTOS,
    ClubSiteService,
)
from app.services.member_service import MemberService
from app.services.site_request_service import SiteRequestService
from app.utils.decorators import permission_required
from app.utils.uploads import save_image

club_public_bp = Blueprint('club_public', __name__)
site_admin_bp = Blueprint('site_admin', __name__)
site_requests_bp = Blueprint('site_requests', __name__)


def _amenities_from_form(form) -> list[dict]:
    rows = []
    for i in range(MAX_AMENITIES):
        rows.append({
            'icon': form.get(f'amenity_icon_{i}') or 'dumbbell',
            'title': form.get(f'amenity_title_{i}') or '',
            'text': form.get(f'amenity_text_{i}') or '',
        })
    return rows


def _public_url_kwargs() -> dict:
    slug = getattr(g, 'tenant_slug', None)
    if saas_enabled() and slug and slug != 'legacy':
        return {'slug': slug}
    return {}


@club_public_bp.route('/')
def landing():
    """Public marketing page for a club (/club/<slug>/)."""
    payload = ClubSiteService.public_payload(require_published=True)
    if not payload:
        abort(404)
    slug = getattr(g, 'tenant_slug', None) or 'legacy'
    return render_template(
        'club/landing.html',
        slug=slug,
        saas=saas_enabled(),
        **payload,
    )


@club_public_bp.route('/request', methods=['POST'], endpoint='request_booking')
@limiter.limit('8 per hour')
@limiter.limit('25 per day')
def request_booking():
    """Booking request from an anonymous visitor: no portal account required."""
    site = ClubSiteService.get()
    if not site.get('is_published'):
        abort(404)
    target = url_for('club_public.landing', **_public_url_kwargs()) + '#booking'
    if not site.get('booking_enabled', True):
        abort(404)
    # Bots fill every field; humans never see this one.
    if (request.form.get('website') or '').strip():
        flash('Заявка отправлена. Мы перезвоним, чтобы подтвердить запись.', 'booking_ok')
        return redirect(target)
    try:
        SiteRequestService.create_public({
            'kind': request.form.get('kind'),
            'session_id': request.form.get('session_id'),
            'slot_id': request.form.get('slot_id'),
            'trainer_id': request.form.get('trainer_id'),
            'full_name': request.form.get('full_name'),
            'phone': request.form.get('phone'),
            'comment': request.form.get('comment'),
        })
        flash('Заявка отправлена. Мы перезвоним, чтобы подтвердить запись.', 'booking_ok')
    except ValueError as exc:
        flash(str(exc), 'booking_error')
    except Exception:
        current_app.logger.exception('Site booking request failed')
        flash('Не получилось отправить заявку. Позвоните нам, пожалуйста.', 'booking_error')
    return redirect(target)


@site_admin_bp.route('/', methods=['GET', 'POST'])
@login_required
@permission_required('manage_club_site')
def edit():
    site = ClubSiteService.get()
    photos = ClubSiteService.list_photos()
    if request.method == 'POST':
        action = request.form.get('action') or 'save'
        try:
            if action == 'delete_photo':
                ClubSiteService.delete_photo(int(request.form.get('photo_id')))
                flash('Фото удалено', 'info')
            elif action == 'update_caption':
                ClubSiteService.update_photo_caption(
                    int(request.form.get('photo_id')),
                    request.form.get('caption') or '',
                )
                flash('Подпись сохранена', 'success')
            elif action in ('move_up', 'move_down'):
                ClubSiteService.move_photo(
                    int(request.form.get('photo_id')),
                    'up' if action == 'move_up' else 'down',
                )
                flash('Порядок галереи обновлён', 'success')
            elif action == 'add_photo':
                path = save_image(request.files.get('photo'), 'club')
                if not path:
                    raise ValueError('Выберите изображение')
                ClubSiteService.add_photo(path, request.form.get('caption') or '')
                flash('Фото добавлено', 'success')
            else:
                hero = None
                if request.files.get('hero_photo') and request.files['hero_photo'].filename:
                    hero = save_image(request.files['hero_photo'], 'club')
                background = None
                background_file = request.files.get('background_photo')
                if background_file and background_file.filename:
                    background = save_image(background_file, 'club')
                ClubSiteService.update(
                    {
                        'headline': request.form.get('headline'),
                        'about_text': request.form.get('about_text'),
                        'phone': request.form.get('phone'),
                        'address': request.form.get('address'),
                        'hours_text': request.form.get('hours_text'),
                        'map_embed_url': request.form.get('map_embed_url'),
                        'hero_photo_path': hero,
                        'theme_preset': request.form.get('theme_preset'),
                        'accent_color': request.form.get('accent_color'),
                        'background_overlay': request.form.get('background_overlay'),
                        'background_photo_path': background,
                        'is_published': request.form.get('is_published') == '1',
                        'hero_kicker': request.form.get('hero_kicker'),
                        'hero_lead': request.form.get('hero_lead'),
                        'cta_label': request.form.get('cta_label'),
                        'about_heading': request.form.get('about_heading'),
                        'gallery_heading': request.form.get('gallery_heading'),
                        'footer_tagline': request.form.get('footer_tagline'),
                        'amenities': _amenities_from_form(request.form),
                        'booking_enabled': request.form.get('booking_enabled') == '1',
                        'booking_note': request.form.get('booking_note'),
                    }
                )
                flash('Сайт сохранён', 'success')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('site_admin.edit'))
    public_url = None
    if saas_enabled():
        slug = getattr(g, 'tenant_slug', None)
        if slug and slug != 'legacy':
            public_url = url_for('club_public.landing', slug=slug)
    else:
        public_url = url_for('club_public.landing')
    return render_template(
        'club/site_admin.html',
        site=site,
        theme=ClubSiteService.theme(site),
        photos=photos,
        public_url=public_url,
        amenity_icons=AMENITY_ICONS,
        amenity_rows=ClubSiteService.amenities_for_form(site),
        max_gallery_photos=MAX_GALLERY_PHOTOS,
        new_requests=SiteRequestService.new_count(),
    )


@site_requests_bp.route('/', methods=['GET', 'POST'])
@login_required
@permission_required('manage_site_requests')
def index():
    if request.method == 'POST':
        action = request.form.get('action') or ''
        request_id = int(request.form.get('request_id') or 0)
        user_id = getattr(current_user, 'id', None)
        try:
            if action == 'confirm':
                result = SiteRequestService.confirm(request_id, user_id)
                if result.get('outcome') == 'waitlisted':
                    flash('Мест нет — клиент добавлен в лист ожидания, заявка закрыта', 'warning')
                else:
                    flash('Клиент записан, заявка закрыта', 'success')
            elif action == 'create_member':
                member = SiteRequestService.create_member_from_request(request_id)
                flash(f"Карточка создана: {member['full_name']} · {member['card_number']}", 'success')
            elif action == 'link_member':
                SiteRequestService.link_member(request_id, int(request.form.get('member_id') or 0))
                flash('Клиент привязан к заявке', 'success')
            elif action == 'note':
                SiteRequestService.save_note(request_id, request.form.get('staff_note') or '')
                flash('Комментарий сохранён', 'success')
            elif action == 'status':
                SiteRequestService.set_status(request_id, request.form.get('status') or '', user_id)
                flash('Статус заявки обновлён', 'success')
            else:
                raise ValueError('Неизвестное действие')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('site_requests.index', status=request.args.get('status')))

    status = request.args.get('status') or 'open'
    return render_template(
        'club/site_requests.html',
        requests=SiteRequestService.list_all(status),
        counts=SiteRequestService.counts(),
        status=status,
        members=MemberService.list_members(limit=500),
        kind_label=SiteRequestService.kind_label,
        status_label=SiteRequestService.status_label,
    )
