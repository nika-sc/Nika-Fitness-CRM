"""Public content routes shared by self-hosted and SaaS editions."""
from flask import Blueprint, abort, current_app, redirect, render_template, url_for
from flask_login import current_user

from app.database.connection import saas_enabled
from app.services.public_content_service import PublicContentService

bp = Blueprint('public', __name__)


@bp.route('/')
def index():
    landing = current_app.extensions.get('saas_landing')
    if landing:
        return landing()
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@bp.route('/docs')
def docs():
    return render_template('public/docs.html')


def _render_docs_page(key: str, *, note: str):
    page = PublicContentService.read_docs_page(key)
    if not page:
        abort(404)
    heading, markdown = page
    return render_template(
        'public/docs_page.html',
        page_heading=heading,
        page_note=note,
        content_html=PublicContentService.markdown_to_html(markdown),
    )


@bp.route('/docs/about')
def docs_about():
    return _render_docs_page(
        'about',
        note=(
            'Бесплатная open-source CRM для фитнес-клубов: что умеет система и как '
            + ('поставить облако SaaS или ' if saas_enabled() else '')
            + 'развернуть на своём сервере (Linux/Windows).'
        ),
    )


@bp.route('/docs/map')
def docs_map():
    return _render_docs_page(
        'map',
        note='Короткая карта: сотрудник, клиент и гость ходят в разные двери. Главная — не рабочее место.',
    )


@bp.route('/docs/guide')
def docs_guide():
    return _render_docs_page(
        'guide',
        note=(
            'Полное руководство бесплатной Nika Fitness CRM — текст открывается '
            'прямо на демо, без обязательного перехода в GitHub.'
        ),
    )


@bp.route('/docs/walkthrough')
def docs_walkthrough():
    return _render_docs_page(
        'walkthrough',
        note='Пошаговый маршрут рабочего дня в бесплатной CRM клуба — прямо на сайте.',
    )


@bp.route('/blog')
def blog():
    posts = PublicContentService.blog_posts()
    return render_template('public/blog_index.html', posts=posts)


@bp.route('/blog/<slug>')
def blog_post(slug: str):
    post = PublicContentService.blog_post(slug)
    if not post:
        abort(404)
    body_html = PublicContentService.markdown_to_html(post.body_markdown)
    return render_template('public/blog_post.html', post=post, body_html=body_html)


@bp.route('/updates')
def updates():
    """Legacy URL — release notes live in /blog."""
    return redirect(url_for('public.blog'), 301)


@bp.route('/health')
def health():
    return {'ok': True, 'saas': saas_enabled(), 'edition': current_app.config.get('APP_EDITION')}, 200
