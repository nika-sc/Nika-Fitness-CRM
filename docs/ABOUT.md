# О проекте и установка

**Nika Fitness CRM** — среда для фитнес-клубов, студий и спортивных центров: ресепшен, абонементы, расписание, личный кабинет клиента и сайт клуба.

Мы создали её, чтобы **учёт клуба был доступным**: без обязательной дорогой подписки можно вести зал на своём сервере (open-source) и познакомиться с продуктом на живом демо. Цель простая и человеческая — **привлечь больше людей к спорту** и **помочь начинающим руководителям** фитнес-центров запускать клуб, популяризировать тренировки и держать порядок в клиентах, визитах и оплатах с первого дня.

- Живое демо: [fitness.nika-crm.ru/demo](https://fitness.nika-crm.ru/demo)
- Бренд-хаб: [nika-crm.ru](https://www.nika-crm.ru/)
- Self-hosted на GitHub: [Nika-Fitness-CRM](https://github.com/nika-sc/Nika-Fitness-CRM)
- Лицензия публичного среза: MIT

Автор: **Александр Смелков**, Сочи.

## Что умеет система

- Ресепшен: чекин, зоны, гости, медсправки, шкафчики
- Абонементы: планы, продажи, заморозка, оплаты и кассовые смены
- Расписание: групповые занятия, запись, waitlist, no-show
- Личный кабинет клиента: запись, QR-пропуск, история визитов
- Публичный сайт клуба: цены, тренеры, расписание, контакты
- Отчёты и обзор клуба для владельца и администратора

Подробно по экранам: [руководство](/docs/guide) и [сценарий рабочего дня](/docs/walkthrough).

## Как начать

| Путь | Когда выбирать |
|------|----------------|
| **[Живое демо](#живое-демо)** | Посмотреть CRM без установки |
| **[Linux / Docker](#linux--docker)** | Свой VPS или сервер, полный контроль данных |
| **[Windows в зале](#windows-в-зале)** | Локальный ПК / мини-сервер в клубе |

## Живое демо

Демо-стенд — [fitness.nika-crm.ru/demo](https://fitness.nika-crm.ru/demo): вход сотрудником демо-клуба (`admin` / `admin123`), личный кабинет клиента и публичный сайт клуба. Данные там вымышленные и периодически сбрасываются.

Подробности развёртывания у себя — в [документации](/docs) и в [DEPLOY.md](https://github.com/nika-sc/Nika-Fitness-CRM/blob/master/docs/DEPLOY.md).

## Linux / Docker

Self-hosted на Linux: Docker Compose, PostgreSQL, reverse-proxy и HTTPS.

```bash
git clone https://github.com/nika-sc/Nika-Fitness-CRM.git
cd Nika-Fitness-CRM
cp .env.example .env
# укажите SECRET_KEY и DATABASE_URL
docker compose up -d
```

Полная инструкция: [docs/DEPLOY.md](https://github.com/nika-sc/Nika-Fitness-CRM/blob/master/docs/DEPLOY.md).

## Windows в зале

Локальный сервер клуба: Python, PostgreSQL, автозапуск службы Windows — CRM работает в сети зала без обязательного облака.

Шаги установки и автозапуск описаны в том же [DEPLOY.md](https://github.com/nika-sc/Nika-Fitness-CRM/blob/master/docs/DEPLOY.md) (раздел Windows). Помощь с установкой — по запросу.

## Помощь и контакты

- Email: [info@nika-sc.ru](mailto:info@nika-sc.ru), [nika-sc@bk.ru](mailto:nika-sc@bk.ru) (тема: «Nika Fitness CRM»)
- Telegram: [t.me/nikaservice](https://t.me/nikaservice)
- Телефон: +7 (938) 418-59-40 · +7 (862) 295-51-05

Если вы только открываете зал или студию — напишите. Поможем выбрать свой сервер или демо и запустить учёт так, чтобы вы занимались людьми и спортом, а не таблицами в Excel.
