# AGENTS.md

This repository contains **h4ckrth0n**, a Python library for shipping hackathon products quickly with strong security and performance defaults.

It is designed to be “import a few lines and ship”, with:
- opinionated batteries included
- secure-by-default authentication and authorization
- PostgreSQL support available immediately (driver included by default)
- LLM tooling included by default (safe defaults and guardrails)
- typed, tested, documented public APIs

## Product principles

1) Ship fast, safely:
- the default path should be the safe path
- “pit of success” for auth and RBAC

2) Opinionated defaults, but composable:
- provide wrapped helpers that do the right thing out of the box
- still allow escape hatches for advanced teams

3) Hackathon realism:
- minimal code to get protected endpoints
- minimal config to get a working database and auth
- predictable conventions over endless knobs

## Non-goals

- Building a hosted platform.
- Replacing every framework in the ecosystem.
- Hiding security trade-offs completely. We automate safe defaults and expose the model clearly.

## Stack (defaults shipped)

- Web/API: FastAPI (ASGI), automatic OpenAPI
- DB: SQLAlchemy 2.x + Alembic
- PostgreSQL driver: Psycopg 3 (binary extra used for fast install in hackathon contexts)
- Auth: Argon2id password hashing, JWT access tokens, refresh tokens (revocable), password reset (single-use)
- Settings: environment-based configuration (pydantic-settings)
- LLM: OpenAI Python SDK included by default, plus a small abstraction layer and redaction hooks
- Redis: OPTIONAL (extra), for background queues or caching

Notes:
- uv is the project manager.
- Keep the public API small and stable.

## Repository layout

- `src/h4ckrth0n/` library code (src layout)
- `tests/` pytest tests
- `examples/` runnable demo apps
- `docs/` docs and decisions

## Setup commands (uv)

- Install and sync:
  - `uv sync`
- Run commands in the project environment:
  - `uv run <command>`
- CI should use locked mode:
  - `uv run --locked pytest`

uv automatically locks and syncs on `uv run`. `--locked` disables auto-lock updates. :contentReference[oaicite:1]{index=1}

## Opinionated defaults to preserve

### AuthN + AuthZ model
- Built-in roles: `user`, `admin`
- JWT claims include:
  - `sub` (user id)
  - `role` (string)
  - `scopes` (list of strings)
  - `iat`, `exp`, and optionally `aud`, `iss`
- Endpoint protection should be easy:
  - decorators or FastAPI dependencies
  - helpers like `require_user()`, `require_admin()`, `require_scopes([...])`

### Secure defaults
- Never log secrets, tokens, Authorization headers, or reset tokens.
- Password reset tokens:
  - random, high-entropy
  - stored hashed
  - time-limited
  - single-use (or revocable)
- Refresh tokens:
  - stored server-side
  - rotated on use
  - revocable (logout revokes)
- Default dev mode should “just work” while still being safe:
  - for production mode, missing critical secrets should be a hard error
  - for dev mode, generate ephemeral secrets and emit clear warnings

### Performance
- No connection leaks. Sessions must close reliably.
- Avoid blocking network calls in the request path unless explicitly documented.
- Provide a small LLM client wrapper that supports timeouts and retries, with sensible defaults.

## Dependency policy

- Default install includes the full hackathon experience:
  - FastAPI, SQLAlchemy, Alembic, psycopg, Argon2, OpenAI SDK
- Redis and background queue integrations must be optional extras.
- Dev tools go in dependency groups (ruff/mypy/pytest). dependency-groups are standardized but not supported by all tools, uv supports them. :contentReference[oaicite:2]{index=2}

## Testing expectations

- Use pytest.
- Provide integration-style tests (SQLite) that cover:
  - signup/login
  - protected endpoint access with role and scopes
  - refresh rotation
  - password reset lifecycle
- Any bug fix must include a regression test.

## Docs expectations

- README quickstart must be runnable and minimal.
- Provide at least one runnable example under `examples/`:
  - SQLite quickstart (zero-config)
  - Postgres variant (config-only, no dependency change)

## Commit hygiene for agents

After changes, run:
- `uv run ruff format .`
- `uv run ruff check .`
- `uv run mypy src`
- `uv run pytest`

If a design choice is non-obvious, add a short note under `docs/decisions/`.
```

Notes on Postgres driver packaging:

* Psycopg recommends installing the binary extra for quick installs in apps (`pip install "psycopg[binary]"`). ([psycopg.org][2])
