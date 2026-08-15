# Установка и деплой — Nika Fitness CRM

Установка на **свой сервер**: Linux (Docker/VPS) или Windows в клубе.

## 1. Linux (Docker / VPS)

Рекомендуемый стек: Ubuntu 22.04+, Docker Compose, Nginx/Caddy, HTTPS.

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

Чеклист reverse-proxy:

- проксирование на порт приложения;
- HTTPS и редирект с HTTP;
- `TRUSTED_HOSTS`, `SESSION_COOKIE_SECURE=1`;
- лимиты размера для uploads.

Бэкапы: `pg_dump` базы клуба, шифрованные копии offsite, тест восстановления раз в месяц.

## 2. Windows (локальный сервер клуба)

1. Установите **Python 3.12+** и **PostgreSQL 18+**.
2. Создайте БД и пропишите `DATABASE_URL` в `.env`.
3. В каталоге проекта:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts/run_migrations.py --legacy --seed-admin
python run.py
```

4. Автозапуск: задача планировщика или служба Windows с `.venv\Scripts\python.exe run.py`.
5. В сети клуба: `http://<IP-сервера>:5001/`.

Для production желательны HTTPS (Caddy/IIS) и регулярные бэкапы PostgreSQL.

## 3. Обновление уже установленной копии

```bash
git pull
python scripts/run_migrations.py --legacy
```

Docker: пересоберите контейнер (`docker compose up -d --build`) — `entrypoint` сам применит новые миграции. После обновления 15.08.2026 нужны миграции `016_trainer_slots` и `017_trainer_slot_confirm` (кабинет тренера и подтверждение заявок).

Затем: **Тренеры** → карточка → **Учётная запись** (сотрудник с ролью «Тренер») — иначе кабинет `/trainer/` покажет, что аккаунт не связан.

## 4. Переменные окружения

```env
APP_EDITION=selfhosted
SECRET_KEY=смените
DATABASE_URL=postgresql://user:pass@host:5432/nika_fitness
APP_PORT=5001
TRUSTED_HOSTS=localhost,127.0.0.1,your.domain
```

Не коммитьте `.env`. Одна база клуба — без мультитенантной платформы.

## 5. Безопасность

- строгий `TRUSTED_HOSTS`;
- secure cookies в production;
- смена пароля admin после установки;
- обновления ОС и зависимостей.

## 6. Поддержка

Помощь с установкой на VPS или Windows — по запросу.  
Кастомные доработки — платные по согласованию.

См. [SUPPORT.md](../SUPPORT.md).
