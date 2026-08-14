"""Safe image uploads (tenant-isolated when SaaS)."""
from __future__ import annotations

import os
import uuid

from flask import current_app, g
from werkzeug.datastructures import FileStorage

from app.database.connection import saas_enabled
from app.utils.security import detect_image_ext


def allowed_image(filename: str) -> bool:
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config['ALLOWED_IMAGE_EXTENSIONS']


def _tenant_subdir() -> str:
    if not saas_enabled():
        return ''
    slug = getattr(g, 'tenant_slug', None) or 'unknown'
    if slug == 'legacy':
        return ''
    return slug


def save_image(file: FileStorage, subdir: str) -> str | None:
    if not file or not file.filename:
        return None
    if not allowed_image(file.filename):
        raise ValueError('Допустимы только JPG, PNG, WEBP')
    header = file.stream.read(16)
    file.stream.seek(0)
    detected = detect_image_ext(header)
    if not detected:
        raise ValueError('Файл не является изображением JPG, PNG или WEBP')
    name = f'{uuid.uuid4().hex}.{detected}'
    tenant = _tenant_subdir()
    parts = [current_app.config['UPLOAD_FOLDER']]
    url_parts = ['uploads']
    if tenant:
        parts.append(tenant)
        url_parts.append(tenant)
    parts.append(subdir)
    url_parts.append(subdir)
    folder = os.path.join(*parts)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    file.save(path)
    url_parts.append(name)
    return '/'.join(url_parts)
