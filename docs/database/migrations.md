# Database and migrations

h4ckath0n ships library-managed Alembic migrations inside the package at
`h4ckath0n.db.migrations`.

## Defaults

- `H4CKATH0N_DATABASE_URL` defaults to `sqlite:///./h4ckath0n.db`.
- `create_app()` calls `Base.metadata.create_all()` to create missing tables.
- `H4CKATH0N_AUTO_UPGRADE=false` by default.
- SQLite is suitable for development. Postgres is recommended for production.

## Operator CLI

Use the installed `h4ckath0n` command for database operations:

```bash
h4ckath0n db ping
h4ckath0n db migrate heads
h4ckath0n db migrate current
h4ckath0n db migrate upgrade --to head --yes
```

## AUTO_UPGRADE behavior

`H4CKATH0N_AUTO_UPGRADE=true` runs packaged migrations to `head` on app startup before serving
requests and before `create_all`.

- In production, auto-upgrade is only performed when explicitly enabled and logs a warning that
  this is an operator decision.
- Without `H4CKATH0N_AUTO_UPGRADE=true`, startup does **not** auto-migrate.

## Mismatch warnings and remediation

Startup and `h4ckath0n db ping` both inspect migration state and warn explicitly when the DB is
behind code migrations.

### Case: DB revision behind head

Run:

```bash
h4ckath0n db migrate upgrade --to head --yes
```

### Case: DB initialized without Alembic versioning

Run:

```bash
h4ckath0n db migrate stamp --to <baseline> --yes
h4ckath0n db migrate upgrade --to head --yes
```

Baseline policy for legacy `create_all` deployments in current releases: use `<baseline>=head`.

## Postgres setup

Example DSN:

```bash
H4CKATH0N_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname
```

The psycopg binary extra is installed by default, so no additional driver install is required.

## Transactional invariants

The last passkey invariant uses `SELECT ... FOR UPDATE` in Postgres to prevent concurrent revokes.
SQLite ignores the lock, which is acceptable for local development but not for multi process safety.
