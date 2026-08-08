# Contributing to Nika Fitness CRM

Thanks for contributing.

## Scope

This repository is the **self-hosted** fitness-club CRM.  
Do not add service-center domain flows (orders/repairs/warehouse from [Nika-Service-CRM](https://github.com/nika-sc/Nika-Service-CRM)).

## Setup

1. Create a virtualenv and install dependencies (`pip install -r requirements.txt`).
2. Copy `.env.example` → `.env` and set `SECRET_KEY` + `DATABASE_URL`.
3. Run migrations: `python scripts/run_migrations.py --legacy --seed-admin`.
4. Start the app: `python run.py`.

See [README.md](README.md) and [docs/DEPLOY.md](docs/DEPLOY.md).

## Pull Requests

- Keep PRs focused and small.
- Include migration + docs updates when the schema changes.
- Sync `database/bootstrap/` when adding PostgreSQL migrations.
- Add short manual test notes in the PR description.

## Security and data

- Never commit `.env` or production secrets.
- Do not commit real personal data or payment details.
- Obfuscate screenshots before publishing.

## Code style

- Python 3.12+, Flask.
- Prefer explicit service-layer logic over route-level SQL.
- Keep templates and static assets merged, not overwritten.
