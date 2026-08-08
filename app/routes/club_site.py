"""Public club landing + staff site editor."""
from __future__ import annotations

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from flask_login import login_required

from app.database.connection import saas_enabled
from app.services.club_site_service import ClubSiteService
from app.utils.decorators import permission_required
from app.utils.uploads import save_image

club_public_bp = Blueprint('club_public', __name__)
site_admin_bp = Blueprint('site_admin', __name__)


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
    )
