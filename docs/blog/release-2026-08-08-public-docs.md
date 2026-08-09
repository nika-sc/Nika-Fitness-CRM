---
title: Релиз 2026-08-08 — публичный OSS и галерея CRM
slug: release-2026-08-08-public-docs
date: 2026-08-08
summary: Self-hosted snapshot на GitHub, подробные гайды со скриншотами, lightbox-галерея на лендинге.
---
## Добавлено

- пакет `app/saas/` и флаг `APP_EDITION`;
- `tools/publish_public.py` + публичные оверлеи README / DEPLOY / SUPPORT;
- скриншоты walkthrough в `docs/assets/walkthrough/`;
- галерея интерфейса на главной с lightbox;
- issue templates и OSS meta для public snapshot.

## Изменено

- USER_GUIDE и USER_WALKTHROUGH — подробные сценарии со скринами, пути self-hosted;
- лендинг: CTA без лишней кнопки «Сайт клуба» в hero, ссылка остаётся в меню;
- CI publish-public: безопасная передача версии через `env:` (без shell-injection).

## Документация

- блог: `public-selfhosted-guides`;
- публичный CHANGELOG и SUPPORT выровнены под self-hosted.
