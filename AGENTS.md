# AGENTS.md

This repository contains **h4ckath0n**, a Python library for shipping hackathon products quickly with strong security and performance defaults.

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

1) Opinionated defaults, but composable:

- provide wrapped helpers that do the right thing out of the box
- still allow escape hatches for advanced teams

1) Hackathon realism:

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
- Auth: Passkeys (WebAuthn) via py_webauthn – default, no passwords required
- Auth (optional): Argon2id password hashing via `h4ckath0n[password]` extra
- JWT: PyJWT with access tokens, refresh tokens (revocable)
- Settings: environment-based configuration (pydantic-settings)
- LLM: OpenAI Python SDK included by default, plus a small abstraction layer and redaction hooks
- Redis: OPTIONAL (extra), for background queues or caching

Notes:

- uv is the project manager.
- Keep the public API small and stable.

## Repository layout

- `src/h4ckath0n/` library code (src layout)
- `tests/` pytest tests
- `examples/` runnable demo apps
- `docs/` docs and decisions
- `packages/create-h4ckath0n/` npm CLI package for scaffolding full-stack projects
- `packages/create-h4ckath0n/templates/fullstack/` embedded project templates (api + web)

## Setup commands (uv)

- Install and sync:
  - `uv sync`
- Run commands in the project environment:
  - `uv run <command>`
- CI should use locked mode:
  - `uv run --locked pytest`

uv automatically locks and syncs on `uv run`. `--locked` disables auto-lock updates.

## CI quality gates

Backend (run from repo root):

- `uv sync --locked --all-extras`
- `uv run --locked ruff format --check .`
- `uv run --locked ruff check .`
- `uv run --locked mypy src`
- `uv run --locked pytest -v`

Frontend (run from `packages/create-h4ckath0n/templates/fullstack/web/`):

- `npm ci`
- `npm run lint`
- `npm run typecheck`
- `npm test`
- `npm run build`

## Release channels

- **dev** (pushes to main): base `X.Y.(Z+1)`, npm `X.Y.(Z+1)-dev.YYYY-MM-DD.HH-MM-SS.<sha7>`, PyPI `X.Y.(Z+1).devYYYYMMDDHHMMSS`, dist-tag `dev`.
- **nightly** (scheduled): base `X.Y.(Z+1)`, npm `X.Y.(Z+1)-dev.YYYY-MM-DD`, PyPI `X.Y.(Z+1).devYYYYMMDD`, dist-tag `nightly`.
- **stable** (tag `vX.Y.Z`): publish `X.Y.Z` with dist-tag `latest`.

PyPI Trusted Publisher must reference workflow `publish.yml` and environment `pypi`.
npm Trusted Publisher must reference workflow `publish.yml` and environment `npm`.

## Opinionated defaults to preserve

### AuthN + AuthZ model

- Default auth: passkeys (WebAuthn) via py_webauthn
- Password auth: optional extra (`h4ckath0n[password]`), off by default
- Built-in roles: `user`, `admin`
- JWT claims include:
  - `sub` (user id)
  - `role` (string)
  - `scopes` (list of strings)
  - `iat`, `exp`, and optionally `aud`, `iss`
- Endpoint protection should be easy:
  - decorators or FastAPI dependencies
  - helpers like `require_user()`, `require_admin()`, `require_scopes([...])`

### ID scheme

- All primary IDs use a 32-character base32 scheme from 20 random bytes
- User IDs: first character forced to `u` (e.g., `u3mfgh7k2n4p5q6r7s8t9v0w1x2y3z4a`)
- Internal credential key IDs: first character forced to `k`
- Helpers: `new_user_id()`, `new_key_id()`, `is_user_id()`, `is_key_id()`
- Never use email as user ID
- WebAuthn credential_id from browser is stored separately (base64url), not as the internal key ID

### Multi-passkey model and last-passkey invariant

- Users can register multiple passkeys
- A user's last active (non-revoked) passkey **cannot be revoked** (LAST_PASSKEY error)
- This check is transactional (SELECT ... FOR UPDATE in Postgres) to prevent race conditions
- Revoked passkeys have `revoked_at` set; they can never be un-revoked

### WebAuthn challenges

- Challenge state stored server-side in `webauthn_challenges` table
- Default TTL: 300 seconds (configurable via `H4CKATH0N_WEBAUTHN_TTL_SECONDS`)
- Challenges are single-use (consumed on successful finish)
- Expired challenges can be cleaned up via `cleanup_expired_challenges()`

### Secure defaults

- Never log secrets, tokens, Authorization headers, WebAuthn assertions, or attestation objects.
- Password reset tokens (password extra only):
  - random, high-entropy
  - stored hashed
  - time-limited
  - single-use (or revocable)
- Refresh tokens:
  - stored server-side
  - rotated on use
  - revocable (logout revokes)
- WebAuthn challenges:
  - stored server-side, single-use, time-limited (default 5 min)
  - origin and rpId validated strictly in production
- Default dev mode should "just work" while still being safe:
  - for production mode, missing critical secrets and WebAuthn settings are a hard error
  - for dev mode, generate ephemeral secrets and use localhost defaults with clear warnings

### Performance

- No connection leaks. Sessions must close reliably.
- Avoid blocking network calls in the request path unless explicitly documented.
- Provide a small LLM client wrapper that supports timeouts and retries, with sensible defaults.

## Observability (killer feature)

h4ckath0n ships LLM + agent frameworks by default and offers opt-in, end-to-end observability.

### Default dependencies for agentic development

- openai (official SDK)
- langchain, langchain-core, langchain-openai
- langgraph
- langsmith (used for tracing/runs, and optionally OpenTelemetry export)

### Opt-in behavior

- Observability is OFF by default.
- When enabled, the library instruments:
  - FastAPI requests
  - LangChain + LangGraph runs (DAG tracing)
  - OpenAI calls (via LangChain integration or wrapped SDK)
  - DB activity (session/query spans)
- Traces must include a stable trace/run id returned to callers.

### Configuration conventions

- h4ckath0n should support both:
  1) LangSmith-native tracing via env vars (LANGSMITH_TRACING, LANGSMITH_API_KEY, LANGSMITH_PROJECT)
  2) OpenTelemetry export when configured (OTEL_* variables)

LangSmith explicitly supports OpenTelemetry-based tracing. Never require users to write custom tracing glue.

### Privacy and redaction

- Tracing must never record secrets (API keys, JWTs, reset tokens, Authorization headers).
- Provide redaction hooks for:
  - prompts, tool args, retrieved documents, and model outputs
- Provide per-route and per-graph controls:
  - disable tracing entirely
  - trace metadata only
  - sampling controls

### Developer ergonomics

- Add a small middleware layer to attach trace_id/run_id to responses.
- Provide helpers to wrap tools and graph nodes so names and metadata are consistent.

## Dependency policy

- Default install includes the full hackathon experience:
  - FastAPI, SQLAlchemy, Alembic, psycopg, py_webauthn, OpenAI SDK
- Password auth (Argon2) is an optional extra: `h4ckath0n[password]`
- Redis and background queue integrations must be optional extras.
- Dev tools go in dependency groups (ruff/mypy/pytest). dependency-groups are standardized but not supported by all tools, uv supports them.

## Dependency updates

### Renovate

- Renovate runs via the GitHub App and is configured in `renovate.json`.
- Current scope (today): `pyproject.toml` (uv-managed), weekly `uv.lock` maintenance, and GitHub Actions workflows.
- Policy: minor/patch updates may automerge only after CI passes; major updates never automerge and require human review.
- If this repo gains new ecosystems (Dockerfiles, npm, cargo, Terraform, etc.), extend `renovate.json` with the correct matchManagers/matchDatasources and grouping while keeping the same automerge policy. Keep the config minimal and truthful by only enabling managers for ecosystems that exist in the repo.

### Keeping dependencies current (uv)

Agents should keep the dependency set healthy and forward-moving.

- Periodically run:
  - `uv sync --upgrade`
- Then fix any compatibility issues that arise:
  - address breaking changes by migrating code forward
  - fix deprecation warnings proactively
- Do not downgrade dependencies to “make things pass” unless the feature we rely on is removed or a security/stability regression forces it. Prefer best-effort migration to newer versions.

When `uv sync --upgrade` changes `uv.lock`, include those changes in the PR with accompanying code fixes and tests.

## Testing expectations

- Use pytest.
- Provide integration-style tests (SQLite) that cover:
  - passkey registration/login flow state
  - ID generators (length, prefix, charset)
  - last-passkey invariant (cannot revoke last active passkey)
  - protected endpoint access with role and scopes
  - refresh rotation
  - password auth lifecycle (when password extra enabled)
- Any bug fix must include a regression test.

## Docs expectations

- README quickstart must be runnable and minimal.
- Provide at least one runnable example under `examples/`:
  - SQLite quickstart (zero-config)
  - Postgres variant (config-only, no dependency change)

## Commit hygiene for agents

### Required pre-commit checks (must run before committing)

Before committing any changes, format the code and run the same checks used in CI (locked mode):

- Format (apply changes):
  - `uv run --locked ruff format .`

- Verify the full CI gate locally:
  - `uv run --locked ruff format --check .`
  - `uv run --locked ruff check .`
  - `uv run --locked mypy src`
  - `uv run --locked pytest -v`

Do not commit code that fails any of the above commands. Fix issues first.

If a design choice is non-obvious, add a short note under `docs/decisions/`.

### Frontend template checks

When modifying files under `packages/create-h4ckath0n/templates/fullstack/web/`, run from that directory:

- `npm run lint` (ESLint)
- `npm run typecheck` (tsc --noEmit)
- `npm run test` (Vitest)
- `npm run build` (production build)

Do not commit frontend template changes that fail these checks.

### OpenAPI codegen and typed client

The frontend template uses **openapi-typescript** and **openapi-fetch** to generate TypeScript types from the backend OpenAPI schema. The generated output is committed to git and must stay in sync with the backend.

**Generated output path:** `packages/create-h4ckath0n/templates/fullstack/web/src/api/generated/`

**When to regenerate:**
- After modifying backend Pydantic models, route signatures, or `response_model` declarations
- After modifying frontend API consumption code

**How to regenerate (requires backend running on port 8000):**

```bash
# From the web template directory:
npm run gen:api
```

Or use the full-stack dev workflow which handles this automatically:

```bash
# From the web template directory:
npm run dev:fullstack
```

**Drift check (must pass before committing):**

```bash
npm run gen:api
git diff --exit-code src/api/generated/
```

CI enforces this: the `frontend` job starts the backend, runs `gen:api`, and fails if the generated output differs from what's committed.

**Type migration rules (enforced):**
- On-wire JSON types (request/response bodies) **must** come from `src/api/generated/schema.ts`. Do not create manual TS interfaces for backend shapes.
- Frontend-only types (UI state, view models, form state) are allowed but must use explicit naming (`FooViewModel`, `FooFormState`) and include a short `/** Frontend-only: ... */` comment.
- If a type mixes backend and frontend-only fields, split it: import the backend type from the generated schema and compose/extend it with a frontend wrapper.
- Do not keep duplicate "DTO" style types. Duplicates are drift vectors.
- All API calls should go through the typed clients in `src/api/client.ts` (`apiClient` for authenticated, `publicApiClient` for unauthenticated endpoints).

### Scaffold CLI checks

When modifying `packages/create-h4ckath0n/bin/` or `packages/create-h4ckath0n/lib/`:

- Run `node packages/create-h4ckath0n/bin/cli.js --help` to verify CLI syntax.
- Test scaffold output with `node packages/create-h4ckath0n/bin/cli.js test-project --no-install --no-git` in a temp directory.
