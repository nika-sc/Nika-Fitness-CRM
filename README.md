<p align="center">
  <a href="https://github.com/nika-sc/Nika-Fitness-CRM">
    <img src="static/foto/gallery-1.jpg" alt="Nika Fitness CRM" width="100%">
  </a>
</p>

# Nika Fit

**Бесплатная open-source CRM для фитнес-клубов**  
Ресепшен · абонементы · расписание · ЛК клиента · сайт клуба · отчёты

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-2d6a4f?style=for-the-badge" alt="MIT"></a>
  <a href="requirements.txt"><img src="https://img.shields.io/badge/Python-3.12%2B-3776ab?style=for-the-badge" alt="Python"></a>
  <a href="docs/DEPLOY.md"><img src="https://img.shields.io/badge/PostgreSQL-16%2B-336791?style=for-the-badge" alt="PostgreSQL"></a>
  <a href="requirements.txt"><img src="https://img.shields.io/badge/Flask-app-000000?style=for-the-badge" alt="Flask"></a>
  <a href="docker-compose.yml"><img src="https://img.shields.io/badge/Docker-Compose-2496ed?style=for-the-badge" alt="Docker"></a>
</p>

<p align="center">
  <a href="#установка"><b>Установка</b></a> ·
  <a href="docs/USER_GUIDE.md"><b>Руководство</b></a> ·
  <a href="docs/USER_WALKTHROUGH.md"><b>Сценарий дня</b></a> ·
  <a href="#скриншоты"><b>Скриншоты</b></a> ·
  <a href="https://github.com/nika-sc/Nika-Fitness-CRM/issues"><b>Issues</b></a> ·
  <a href="#лицензия-и-контакты"><b>Связаться</b></a>
</p>

> **Не хотите разбираться с установкой сами?**  
> Помогу развернуть CRM на **Linux VPS** или **Windows в зале** (Docker, домен, HTTPS, бэкапы) — по запросу.  
> Кастомные доработки и интеграции — платные по согласованию.  
> Напишите на **info@nika-sc.ru** с темой **Nika Fit — помощь по установке**.  
> Либо поставьте сами по разделам [Установка](#установка) и [docs/DEPLOY.md](docs/DEPLOY.md).

---

CRM для работы клуба: стойка ресепшена, клиенты и абонементы, групповое расписание, личный кабинет с QR-пропуском, публичный сайт клуба и операционные отчёты.

Система рассчитана на **свой сервер**:

- локально в сети клуба (Windows);
- на VPS / Docker с вашим доменом (Linux);
- полный контроль данных клуба в одной PostgreSQL.

Это **не** CRM сервисного центра. Сервисные заказы/склад/ремонты — отдельный продукт: [nika-sc/Nika-Service-CRM](https://github.com/nika-sc/Nika-Service-CRM).

Если нашли баг или хотите предложить улучшение — [Issues](https://github.com/nika-sc/Nika-Fitness-CRM/issues) или письмо на `info@nika-sc.ru` с темой `Nika Fit`.

## Репозиторий

```bash
git clone https://github.com/nika-sc/Nika-Fitness-CRM.git
cd Nika-Fitness-CRM
```

Публичная OSS-версия: [github.com/nika-sc/Nika-Fitness-CRM](https://github.com/nika-sc/Nika-Fitness-CRM)

## Содержание

- [Описание](#описание)
- [Основные функции](#основные-функции)
- [Скриншоты](#скриншоты)
- [Установка](#установка)
  - [Быстрый старт](#быстрый-старт)
  - [Linux (Docker / VPS)](#linux-docker--vps)
  - [Windows (сервер в зале)](#windows-сервер-в-зале)
- [После установки](#после-установки)
- [Архитектура](#архитектура)
- [Документация](#документация)
- [Скрипты](#скрипты)
- [Безопасность](#безопасность)
- [Contributing](#contributing)
- [История изменений](#история-изменений)
- [Лицензия и контакты](#лицензия-и-контакты)

---

## Описание

Современная CRM на **Flask** со слоями:

- **Routes** — HTTP и формы
- **Services** — бизнес-логика клуба
- **Migrations** — схема PostgreSQL (`docs` + `app/database/migrations`)
- **Database** — **PostgreSQL** (обязательно; см. bootstrap-дамп в `database/bootstrap/`)

Обучение с нуля: [пошаговый сценарий рабочего дня](docs/USER_WALKTHROUGH.md) (вход → ресепшен → клиент → запись → отчёты).  
Полный справочник UI: [руководство пользователя](docs/USER_GUIDE.md).

## Основные функции

### Ресепшен и посещения

- Стойка ресепшена: поиск клиента, чекин по номеру карты / QR из ЛК
- Выбор зоны доступа (зал и др.)
- Гостевые визиты с оплатой
- Алерты и контроль истекающих абонементов

### Клиенты и абонементы

- Карточка клиента, статусы, поиск
- Планы абонементов (срок, лимит визитов, цена)
- Продажа абонемента, заморозки, оплаты и долги
- Журнал платежей

### Расписание и тренеры

- Недельное расписание групповых занятий
- Типы занятий, запись, waitlist, no-show
- Справочник тренеров

### Личный кабинет клиента

- Вход по телефону / email / карте
- Цифровой абонемент и **QR-пропуск** для стойки
- Запись на занятия и отмена из ЛК
- История визитов и оплат

### Сайт клуба

- Публичная витрина клуба (`/club/`)
- Редактор контента и темы из CRM
- Галерея, карта, контакты

### Отчёты, роли и настройки

- Dashboard owner/admin: KPI, записи из ЛК, группы дня, чекины
- Отчёты по операциям клуба
- RBAC: `owner` / `admin` / `reception` / `trainer`
- Настройки клуба, сотрудников, прав

### Дополнительные модули

- PT-пакеты, сообщения, зоны доступа
- Корпоративные клиенты, кассовые смены, шкафчики
- Лояльность, лиды, филиалы
- Онлайн-оплаты (stub/adapters), SPA/бар, киоск, NPS

## Скриншоты

<p align="center"><strong>Dashboard</strong> · <strong>Ресепшен</strong></p>
<p align="center">
  <img src="static/foto/shot-dashboard.jpg" alt="Dashboard CRM" width="48%">
  &nbsp;
  <img src="static/foto/shot-reception.jpg" alt="Ресепшен" width="48%">
</p>

<p align="center"><strong>Клиенты</strong> · <strong>Расписание</strong></p>
<p align="center">
  <img src="static/foto/shot-members.jpg" alt="Клиенты" width="48%">
  &nbsp;
  <img src="static/foto/shot-schedule.jpg" alt="Расписание" width="48%">
</p>

<p align="center"><strong>ЛК клиента</strong> · <strong>Абонементы</strong></p>
<p align="center">
  <img src="static/foto/shot-portal.jpg" alt="Личный кабинет клиента" width="48%">
  &nbsp;
  <img src="static/foto/shot-memberships.jpg" alt="Абонементы" width="48%">
</p>

<p align="center"><strong>Отчёты</strong> · <strong>Сайт клуба</strong></p>
<p align="center">
  <img src="static/foto/shot-reports.jpg" alt="Отчёты" width="48%">
  &nbsp;
  <img src="static/foto/shot-club-site.jpg" alt="Публичный сайт клуба" width="48%">
</p>

<p align="center"><strong>Настройки</strong></p>
<p align="center">
  <img src="static/foto/shot-settings.jpg" alt="Настройки CRM" width="72%">
</p>

---

## Установка

Нужны **Python 3.12+** и **PostgreSQL 16+** (или Docker Compose на Linux).

### Быстрый старт

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
# source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env
# задайте SECRET_KEY и DATABASE_URL
python scripts/run_migrations.py --legacy --seed-admin
python run.py
```

Откройте:

- сотрудники: `http://127.0.0.1:5001/login`
- документация на сервере: `/docs`
- ЛК клиента: `/portal`
- сайт клуба: `/club/`

После seed: пользователь `admin` (пароль из `ADMIN_PASSWORD` или `admin123` — смените сразу).

### Linux (Docker / VPS)

```bash
git clone https://github.com/nika-sc/Nika-Fitness-CRM.git
cd Nika-Fitness-CRM
cp .env.example .env
# SECRET_KEY, DATABASE_URL, TRUSTED_HOSTS
docker compose up -d --build
```

Миграции при необходимости:

```bash
python scripts/run_migrations.py --legacy --seed-admin
```

Подробно: [docs/DEPLOY.md](docs/DEPLOY.md).

### Windows (сервер в зале)

1. Установите Python 3.12+ и PostgreSQL 16+.
2. Создайте БД и пропишите `DATABASE_URL` в `.env`.
3. Выполните быстрый старт выше.
4. Автозапуск: служба Windows или Планировщик задач (`.venv\Scripts\python.exe run.py`).
5. В сети клуба: `http://<IP-сервера>:5001/`.

Для production желательны HTTPS (Caddy/IIS) и регулярные бэкапы PostgreSQL.

### Переменные окружения (минимум)

```env
APP_EDITION=selfhosted
SECRET_KEY=смените
DATABASE_URL=postgresql://user:pass@host:5432/nika_fitness
APP_PORT=5001
TRUSTED_HOSTS=localhost,127.0.0.1,your.domain
```

Полный пример: [`.env.example`](.env.example). Не коммитьте `.env`.

---

## После установки

- Reverse-proxy (Nginx/Caddy) → порт приложения
- HTTPS и редирект с HTTP
- `TRUSTED_HOSTS`, в production — secure cookies
- Бэкапы: `pg_dump` базы клуба, offsite-копии, тест восстановления
- Смена пароля `admin` сразу после первого входа

Чеклист: [docs/DEPLOY.md](docs/DEPLOY.md).

---

## Архитектура

- **Один клуб — одна PostgreSQL** (`DATABASE_URL`)
- App factory (`app/__init__.py`), blueprints по доменам
- Сервисный слой без SQL в шаблонах
- Миграции: `python scripts/run_migrations.py --legacy`
- Bootstrap-схема: `database/bootstrap/`
- Эта редакция — **self-hosted only** (без облачной мультитенантной платформы)

Стек: Flask · Flask-Login · Flask-WTF (CSRF) · PostgreSQL · AdminLTE 4.2.0 / Bootstrap 5.3.8 (vendored, MIT) · (опционально) Docker Compose.

---

## Документация

| Документ | О чём |
|----------|--------|
| [USER_GUIDE.md](docs/USER_GUIDE.md) | Руководство оператора по разделам CRM |
| [USER_WALKTHROUGH.md](docs/USER_WALKTHROUGH.md) | Сценарий рабочего дня |
| [DEPLOY.md](docs/DEPLOY.md) | Linux / Windows, proxy, бэкапы |
| [CHANGELOG.md](docs/CHANGELOG.md) | История изменений |
| [OPEN_SOURCE_CHECKLIST.md](docs/OPEN_SOURCE_CHECKLIST.md) | Проверки перед релизом OSS |
| [SUPPORT.md](SUPPORT.md) | Поддержка и коммерческие услуги |
| [SECURITY.md](SECURITY.md) | Политика безопасности |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Как контрибьютить |

На работающем сервере также доступны `/docs`, `/blog`, `/updates`.

---

## Скрипты

```bash
# Миграции + seed admin (self-hosted)
python scripts/run_migrations.py --legacy --seed-admin

# Запуск dev-сервера
python run.py

# Проверка маршрутов self-hosted (если есть зависимости)
python scripts/smoke_editions.py
```

Docker: `docker compose up --build` (см. `docker-compose.yml`, `docker/Dockerfile`).

---

## Безопасность

В проекте по умолчанию:

- вход сотрудников через Flask-Login + хеш паролей
- RBAC и декоратор прав
- CSRF на state-changing формах
- HttpOnly / SameSite cookies; Secure в production
- whitelist загрузок изображений, UUID-имена файлов
- `TRUSTED_HOSTS` и ProxyFix за reverse-proxy

Уязвимости: не открывайте публичный issue сразу — см. [SECURITY.md](SECURITY.md).

---

## Contributing

Спасибо за вклад. Репозиторий — **только фитнес-клуб**.  
Не переносите сюда домен сервисного центра (заявки/склад/ремонты).

Правила: [CONTRIBUTING.md](CONTRIBUTING.md).  
PR: маленькие, с миграциями/доками при изменении схемы, без `.env` и персональных данных.

---

## История изменений

См. [docs/CHANGELOG.md](docs/CHANGELOG.md).

---

## Лицензия и контакты

- Лицензия: **MIT** — [`LICENSE`](LICENSE)
- Issues: [github.com/nika-sc/Nika-Fitness-CRM/issues](https://github.com/nika-sc/Nika-Fitness-CRM/issues)
- Почта: `info@nika-sc.ru`
- Помощь с установкой VPS / Windows — по запросу
- Кастомные доработки — платные по согласованию

Репозиторий: [`nika-sc/Nika-Fitness-CRM`](https://github.com/nika-sc/Nika-Fitness-CRM)
