# AGENTS.md

This repository contains **h4ckath0n**, a Python library for shipping hackathon products quickly with strong security and performance defaults.

It is designed to be “import a few lines and ship”, with:

- opinionated batteries included
- secure-by-default authentication and authorization
- PostgreSQL support available immediately (driver included by default)
- LLM tooling included by default (safe defaults and guardrails)
- typed, tested, documented public APIs
- a full-stack scaffold CLI (npm) for a working app template (api + web)

## Product principles

1) Ship fast, safely:

- the default path should be the safe path
- “pit of success” for auth and authorization

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
- Auth (user): Passkeys (WebAuthn) via py_webauthn (default, no passwords required)
- Auth (device): browser/device identity keypair (P-256, non-extractable) stored in IndexedDB
- Request auth: client-minted short-lived JWTs signed with the device key (ES256)
- Auth (optional): Argon2id password hashing via `h4ckath0n[password]` extra (only when explicitly enabled)
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

## Source-of-truth security docs

- `docs/security/frontend.md` is the source of truth for the frontend/device-key auth design.
- Documentation must never describe legacy “server-minted access + refresh token” flows unless explicitly reintroduced.

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

E2E (Playwright, run from `packages/create-h4ckath0n/templates/fullstack/web/`):

- Must pass in CI and is a required local quality guard for agents.
- Agents must run E2E locally before submitting work that touches auth, passkeys, device auth, or OpenAPI/type generation.

## Release channels

- **dev** (pushes to main): base `X.Y.(Z+1)`, npm `X.Y.(Z+1)-dev.YYYY-MM-DD.HH-MM-SS.<sha7>`, PyPI `X.Y.(Z+1).devYYYYMMDDHHMMSS`, dist-tag `dev`.
- **nightly** (scheduled): base `X.Y.(Z+1)`, npm `X.Y.(Z+1)-dev.YYYY-MM-DD`, PyPI `X.Y.(Z+1).devYYYYMMDD`, dist-tag `nightly`.
- **stable** (tag `vX.Y.Z`): publish `X.Y.Z` with dist-tag `latest`.

PyPI Trusted Publisher must reference workflow `publish.yml` and environment `pypi`.
npm Trusted Publisher must reference workflow `publish.yml` and environment `npm`.

## Opinionated defaults to preserve

### AuthN + AuthZ model

#### User authentication (passkeys)

- Default auth: passkeys (WebAuthn) via py_webauthn.
- Password auth is optional (`h4ckath0n[password]`) and should remain OFF by default.

#### Device authentication (client-signed ES256 JWT)

Each browser/device maintains a long-lived device identity key:

- Private key: generated via WebCrypto as non-extractable and stored in IndexedDB (via idb-keyval).
- Public key: exported as JWK and registered with the backend.
- Device IDs use the `d...` prefix and are stored server-side bound to a user (`u...`).

For API calls, the web client mints short-lived JWTs signed by the device private key (ES256):

- JWT header includes `kid` set to the device id (`d...`).
- JWT payload includes only identity and time claims (`sub`, `iat`, `exp`), plus optional `aud` and `jti`.
- The JWT contains NO privilege claims: no role, no scopes, no permissions.
- Authorization is computed server-side by loading the user record and enforcing policy from the database.

Server verification flow:

1) Extract `Authorization: Bearer <jwt>`.
2) Read `kid` from JWT header, load device public key from DB.
3) Verify signature (ES256) and time claims.
4) Confirm device is not revoked.
5) Load user bound to the device.
6) Enforce authorization based on DB state, not JWT claims.

#### Authorization model

- Built-in roles: `user`, `admin` (stored server-side).
- Future “user-defined roles” (if added) must also be stored server-side and enforced by server-side policy.
- Endpoint protection should be easy:
  - decorators or FastAPI dependencies
  - helpers like `require_user()`, `require_admin()`, `require_scopes([...])`
- These helpers must not rely on JWT privilege claims (the client token has none).

### ID scheme

- All primary IDs use a 32-character base32 scheme from 20 random bytes
- User IDs: first character forced to `u` (e.g., `u3mfgh7k2n4p5q6r7s8t9v0w1x2y3z4a`)
- Internal credential key IDs: first character forced to `k`
- Device IDs: first character forced to `d`
- Helpers: `new_user_id()`, `new_key_id()`, `new_device_id()`, `is_user_id()`, `is_key_id()`, `is_device_id()`
- Never use email as user ID
- WebAuthn credential_id from browser is stored separately (base64url), not as the internal key ID

### Multi-passkey model and last-passkey invariant

- Users can register multiple passkeys
- A user's last active (non-revoked) passkey **cannot be revoked** (LAST_PASSKEY error)
- This check is transactional (SELECT ... FOR UPDATE in Postgres) to prevent race conditions
- Revoked passkeys have `revoked_at` set; they can never be un-revoked

### WebAuthn challenges

- Challenge state stored server-side (table: `webauthn_challenges`)
- Default TTL: 300 seconds (configurable via `H4CKATH0N_WEBAUTHN_TTL_SECONDS`)
- Challenges are single-use (consumed on successful finish)
- Expired challenges can be cleaned up via `cleanup_expired_challenges()`

### Secure defaults

- Never log secrets, tokens, Authorization headers, WebAuthn assertions, or attestation objects.
- Tokens are short-lived and minted client-side; do not persist tokens to localStorage/sessionStorage.
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

## OpenAPI and frontend type alignment (must stay in sync)

Goal: avoid hand-maintained duplicated types across api and web.

Required artifacts (checked into git):

- `packages/create-h4ckath0n/templates/fullstack/api/openapi.json`
- `packages/create-h4ckath0n/templates/fullstack/web/src/api/openapi.ts`

Rules:

- `openapi.json` must be regenerated when backend API changes.
- `openapi.ts` must be regenerated from `openapi.json` using the pinned generator installed in the web template.
- Generator drift is expected and is pinned by the web template’s `package-lock.json` (generator resolved from local `node_modules`).
- Do not call `npx` inside Node.js source files.
- Use `npm exec --no -- ...` when invoking Node-based generators from scripts/CI to ensure pinned versions and avoid implicit installs.

The generated types must be demonstrated as usable:

- At least one web template file must import types from `src/api/openapi.ts` and use them in the API client layer (not just in tests).
- The web template must typecheck against the generated types in normal dev and CI paths.

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
  - WebAuthn challenge TTL and single-use behavior
  - ID generators (length, prefix, charset)
  - last-passkey invariant (cannot revoke last active passkey)
  - device registration and revocation
  - token verification behavior:
    - `kid` lookup, signature verification (ES256), exp/iat checks, aud separation (http vs ws)
  - protected endpoint access based on server-side DB authorization
  - password auth lifecycle (when password extra enabled)
- Any bug fix must include a regression test.

E2E (Playwright) should cover:

- passkey registration and login flows in the scaffolded web + api
- device key registration and device-signed requests
- passkey management UI for listing and last-passkey revoke block
- OpenAPI type generation being usable in the web app (smoke coverage)

## Docs expectations

- README quickstart must be runnable and minimal.
- Docs must not mention refresh tokens or server-minted access tokens unless that functionality is intentionally reintroduced.
- Keep `docs/security/frontend.md` aligned with implementation.

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

### E2E quality guard (required)

When modifying auth, passkeys, device auth, scaffolding, or OpenAPI/type generation:

- Run Playwright E2E locally and ensure it passes.
- Ensure the CI `e2e` job also passes.

### Scaffold CLI checks

When modifying `packages/create-h4ckath0n/bin/` or `packages/create-h4ckath0n/lib/`:

- Run `node packages/create-h4ckath0n/bin/cli.js --help` to verify CLI syntax.
- Test scaffold output with `node packages/create-h4ckath0n/bin/cli.js test-project --no-install --no-git` in a temp directory.
- Ensure the scaffolded project can run web/api checks and E2E.
