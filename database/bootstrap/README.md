# Bootstrap dump

Для новых установок без пошаговых миграций здесь хранится sanitised SQL-дамп.

Текущий tip схемы: **017_trainer_slot_confirm** (`schema_migrations_pg` → `001`…`017`).

Файл: [`nikafit_public_sanitized.sql`](nikafit_public_sanitized.sql) — DDL + seed + отметки миграций `001`–`017`.

Пересборка с живой БД после `docker compose up`:

```bash
pg_dump -h 127.0.0.1 -p 5433 -U nikafit -d nika_fitness --no-owner --no-acl > database/bootstrap/nikafit_public_sanitized.sql
```

При добавлении новых `00N_*.sql` обязательно обновляйте дамп и этот README.
