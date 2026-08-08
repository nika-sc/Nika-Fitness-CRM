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
    sections = PublicContentService.docs_sections()
    return render_template('public/docs.html', sections=sections)


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
    items = PublicContentService.updates()
    rendered = [
        {
            'entry': item,
            'body_html': PublicContentService.markdown_to_html(item.body_markdown),
        }
        for item in items
    ]
    return render_template('public/updates.html', items=rendered)


@bp.route('/health')
def health():
    return {'ok': True, 'saas': saas_enabled(), 'edition': current_app.config.get('APP_EDITION')}, 200
