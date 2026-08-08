# Nika Fitness CRM (self-hosted)

CRM для фитнес-клубов: установка на **свой сервер** — Linux (Docker/VPS) или Windows в зале.

Ресепшен, абонементы, расписание, ЛК клиента, сайт клуба — полноценная локальная / VPS-версия без облачной платформы SaaS.

Облачная SaaS-версия доступна отдельно по запросу.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](requirements.txt)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%2B-336791.svg)](docs/DEPLOY.md)

[Документация](docs/USER_GUIDE.md) · [Сценарий дня](docs/USER_WALKTHROUGH.md) · [Установка](docs/DEPLOY.md) · [Поддержка](SUPPORT.md)

## Режимы установки

| Режим | Для кого | Как |
|-------|----------|-----|
| **Linux** | VPS / свой сервер | Docker Compose, PostgreSQL, reverse-proxy + HTTPS |
| **Windows** | Сервер в зале | Python + PostgreSQL, автозапуск службы |

## Возможности

- Ресепшен: чекин, гости, алерты, истекающие абонементы
- Абонементы, заморозки, оплаты, долги, кассовые смены
- Групповые занятия: запись, waitlist, no-show
- ЛК клиента: запись, аналитика визитов, оплаты, QR
- Публичный сайт клуба и редактор в CRM
- Dashboard owner/admin

## Быстрый старт

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux
pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env
# задайте DATABASE_URL и SECRET_KEY
python scripts/run_migrations.py --legacy --seed-admin
python run.py
```

Откройте `http://127.0.0.1:5001/login` · документация `/docs`.

## Docker (Linux)

```bash
docker compose up --build
```

## Документация

- `docs/USER_GUIDE.md` — руководство оператора
- `docs/USER_WALKTHROUGH.md` — сценарий рабочего дня
- `docs/DEPLOY.md` — Linux / Windows
- `docs/CHANGELOG.md` — история изменений

## OSS

- Лицензия: MIT (`LICENSE`)
- `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`
- Не коммитить: `.env`, персональные uploads

Публичный репозиторий: [`nika-sc/Nika-Fitness-CRM`](https://github.com/nika-sc/Nika-Fitness-CRM)
