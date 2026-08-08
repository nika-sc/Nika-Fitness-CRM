# Contributing to Nika Fitness CRM

Thanks for contributing.

## Scope

This repository is for **fitness-club CRM** only.  
Do not add service-center domain flows (orders/repairs/warehouse from another product line).

## Setup

1. Create virtual env and install dependencies.
2. Configure `.env` from `.env.example`.
3. Run migrations for platform and tenants.
4. Start app with `python run.py`.

## Pull Requests

- Keep PRs focused and small.
- Include migration + docs updates when schema changes.
- For tenant migrations, sync bootstrap files as required.
- Add manual test notes in PR description.

## Security and data

- Never commit `.env` or production secrets.
- Do not commit real personal data or payment details.
- Obfuscate screenshots before publishing.

## Code style

- Python 3.12+, Flask.
- Prefer explicit service-layer logic over route-level SQL.
- Keep templates and static assets merged, not overwritten.
