# Database and migrations

h4ckath0n ships SQLAlchemy models and creates tables on startup. Alembic is installed as a
dependency, but migration scaffolding is not generated for you.

## Defaults

- `H4CKATH0N_DATABASE_URL` defaults to `sqlite:///./h4ckath0n.db`.
- `create_app()` calls `Base.metadata.create_all()` to create missing tables.
- SQLite is suitable for development. Postgres is recommended for production.

## Postgres setup

Example DSN:

```
H4CKATH0N_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname
```

The psycopg binary extra is installed by default, so no additional driver install is required.

## Transactional invariants

The last passkey invariant uses `SELECT ... FOR UPDATE` in Postgres to prevent concurrent revokes.
SQLite ignores the lock, which is acceptable for local development but not for multi process safety.

## Suggested Alembic workflow

If you need migrations, initialize Alembic inside your app project:

1. `alembic init alembic`
2. Configure the SQLAlchemy URL in `alembic.ini` or env vars.
3. Import your models in `alembic/env.py` so `autogenerate` can see metadata.
4. Run `alembic revision --autogenerate -m "<message>"`.
5. Apply with `alembic upgrade head`.

This workflow is not scaffolded in the template today, so treat it as a manual setup step.
