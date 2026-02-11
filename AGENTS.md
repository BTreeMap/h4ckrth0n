# AGENTS.md

This repository contains **h4ckath0n**, a Python library for shipping hackathon products quickly with secure defaults.

It is designed to be import a few lines and ship, with:

- opinionated batteries included
- secure by default authentication and authorization
- PostgreSQL ready database defaults
- a small LLM wrapper on top of the OpenAI SDK
- typed, tested, documented public APIs
- a full stack scaffold CLI (npm) for a working app template (api and web)

## Product principles

1) Ship fast, safely:

- the default path should be the safe path
- a pit of success for auth and authorization

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
- Hiding security tradeoffs completely. We automate safe defaults and expose the model clearly.

## Stack (defaults shipped)

- Web API: FastAPI (ASGI), automatic OpenAPI
- DB: SQLAlchemy 2.x with `Base.metadata.create_all` on startup
- PostgreSQL driver: psycopg 3 (binary extra used for fast install)
- Auth (user): Passkeys (WebAuthn) via `webauthn`
- Auth (device): browser device identity keypair (P 256, non extractable) stored in IndexedDB
- Request auth: client minted ES256 JWTs signed by the device key
- Auth (optional): Argon2 password hashing via `h4ckath0n[password]` extra
- Settings: environment based configuration (pydantic settings)
- LLM: OpenAI SDK wrapper with timeouts and retries
- Observability: trace id middleware and LangSmith env wiring (no automatic tracing)
- Redis: optional dependency only, no built in integration

Notes:

- uv is the project manager.
- Keep the public API small and stable.

## Repository layout

- `src/h4ckath0n/` library code (src layout)
- `tests/` pytest tests
- `examples/` runnable demo apps
- `docs/` docs and decisions
- `packages/create-h4ckath0n/` npm CLI package for scaffolding full stack projects
- `packages/create-h4ckath0n/templates/fullstack/` embedded project templates (api and web)

## Source of truth security docs

- `docs/security/frontend.md` is the source of truth for the frontend device key auth design.
- Documentation must never describe server minted access plus refresh token flows unless reintroduced.

## Setup commands (uv)

- Install and sync:
  - `uv sync`
- Run commands in the project environment:
  - `uv run <command>`
- CI should use locked mode:
  - `uv run --locked pytest`

uv automatically locks and syncs on `uv run`. `--locked` disables auto lock updates.

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

- Must pass in CI when available.
- Regardless of CI availability, it is a required local quality guard for agents.
- Agents must run E2E locally before submitting work that touches auth, passkeys, device auth,
  scaffolding, or OpenAPI type generation.
- If the agent cannot run CI or add or modify CI jobs, run E2E locally in a CI equivalent way
  (install browsers and deps, then run tests) to match workflow steps.

## Release channels

- **dev** (pushes to main): base `X.Y.(Z+1)`, npm `X.Y.(Z+1)-dev.YYYY-MM-DD.HH-MM-SS.<sha7>`,
  PyPI `X.Y.(Z+1).devYYYYMMDDHHMMSS`, dist tag `dev`.
- **nightly** (scheduled): base `X.Y.(Z+1)`, npm `X.Y.(Z+1)-dev.YYYY-MM-DD`,
  PyPI `X.Y.(Z+1).devYYYYMMDD`, dist tag `nightly`.
- **stable** (tag `vX.Y.Z`): publish `X.Y.Z` with dist tag `latest`.

PyPI Trusted Publisher must reference workflow `publish.yml` and environment `pypi`.
npm Trusted Publisher must reference workflow `publish.yml` and environment `npm`.

## Opinionated defaults to preserve

### AuthN and AuthZ model

#### User authentication (passkeys)

- Default auth is passkeys (WebAuthn) via `webauthn`.
- Password auth is optional (`h4ckath0n[password]`) and should remain off by default.

#### Device authentication (client signed ES256 JWT)

Each browser device maintains a long lived device identity key:

- Private key is generated via WebCrypto as non extractable and stored in IndexedDB.
- Public key is exported as JWK and registered with the backend.
- Device IDs use the `d...` prefix and are stored server side bound to a user (`u...`).

For API calls, the web client mints short lived JWTs signed by the device private key (ES256):

- JWT header includes `kid` set to the device id (`d...`).
- JWT payload includes only identity and time claims (`sub`, `iat`, `exp`, optional `aud`).
- The JWT contains no privilege claims. Authorization is computed server side from the database.

Server verification flow:

1) Extract `Authorization: Bearer <jwt>`.
2) Read `kid` from the JWT header, load device public key from DB.
3) Verify signature (ES256) and time claims.
4) Confirm device is not revoked.
5) Load user bound to the device.
6) Enforce authorization based on DB state, not JWT claims.

#### Authorization model

- Built in roles: `user`, `admin` (stored server side).
- Scopes are stored as a comma separated string on the user record.
- Helpers like `require_user()`, `require_admin()`, `require_scopes([...])` enforce access.
- These helpers must not rely on JWT privilege claims.

### ID scheme

- User IDs use a 32 character base32 scheme from 20 random bytes, prefixed with `u`.
- Internal credential key IDs use the same scheme with `k`.
- Device IDs use the same scheme with `d`.
- Password reset tokens use UUID hex instead of base32.
- Helpers: `new_user_id()`, `new_key_id()`, `new_device_id()`, `new_token_id()`,
  `is_user_id()`, `is_key_id()`, `is_device_id()`.
- Never use email as user ID.
- WebAuthn credential id from the browser is stored separately, not as the internal key ID.

### Multi passkey model and last passkey invariant

- Users can register multiple passkeys.
- A user's last active passkey cannot be revoked (LAST_PASSKEY error).
- This check is transactional with `SELECT ... FOR UPDATE` in Postgres.
- Revoked passkeys have `revoked_at` set and cannot be un revoked.

### WebAuthn challenges

- Challenge state is stored server side (table `webauthn_challenges`).
- Default TTL is 300 seconds (`H4CKATH0N_WEBAUTHN_TTL_SECONDS`).
- Challenges are single use, consumed on successful finish.
- Expired challenges can be cleaned up via `cleanup_expired_challenges()`.

### Secure defaults

- Avoid logging secrets, tokens, authorization headers, or WebAuthn payloads.
- Tokens are short lived and minted client side. Do not persist them in localStorage or cookies.
- WebAuthn origin and RP ID are strict in production. Development defaults to localhost with warnings.

### Performance

- No connection leaks. Sessions must close reliably.
- Avoid blocking network calls in the request path unless documented.

## OpenAPI and frontend type alignment

Goal: avoid hand maintained duplicated types across api and web.

Required artifacts (checked into git):

- `packages/create-h4ckath0n/templates/fullstack/api/openapi.json`
- `packages/create-h4ckath0n/templates/fullstack/web/src/api/openapi.ts`

Rules:

- `openapi.json` must be regenerated when backend API changes.
- `openapi.ts` must be regenerated from `openapi.json` using the pinned generator installed in the
  web template.
- Generator drift is expected and pinned by the web template `package-lock.json`.
- Do not call `npx` inside Node.js source files.
- Use `npm exec --no -- ...` when invoking Node based generators from scripts or CI.

The generated types must be demonstrated as usable:

- At least one web template file must import types from `src/api/openapi.ts` and use them in the API
  client layer (not just in tests).
- The web template must typecheck against the generated types in normal dev and CI paths.

## Observability

Current behavior:

- `init_observability()` adds an `X-Trace-Id` header to each response.
- When `ObservabilitySettings.langsmith_tracing` is true, it sets the LangSmith environment variables
  for downstream tooling.
- `redact_headers`, `redact_value`, `traced_tool`, and `traced_node` provide helpers, but no tracing
  backend is wired by default.

Planned work belongs in a clearly labeled Roadmap section in docs.

## Dependency policy

- Default install includes FastAPI, SQLAlchemy, psycopg, WebAuthn, and the OpenAI SDK.
- LangChain, LangGraph, and LangSmith are included as dependencies but not pre wired.
- Password auth is an optional extra: `h4ckath0n[password]`.
- Redis is an optional extra and only adds the dependency.

## Dependency updates

### Renovate

- Renovate runs via the GitHub App and is configured in `renovate.json`.
- Current scope: `pyproject.toml` (uv managed), weekly `uv.lock` maintenance, and GitHub Actions.
- Policy: minor and patch updates may automerge only after CI passes. Major updates never automerge.
- If this repo gains new ecosystems (Dockerfiles, npm, cargo, Terraform), extend `renovate.json` with
  the correct managers and grouping while keeping the same automerge policy.

### Keeping dependencies current (uv)

Agents should keep the dependency set healthy and forward moving.

- Periodically run: `uv sync --upgrade`.
- Fix compatibility issues by migrating code forward and addressing deprecations.
- Do not downgrade dependencies to make tests pass unless a regression forces it.

When `uv sync --upgrade` changes `uv.lock`, include those changes with code fixes and tests.

## Testing expectations

- Use pytest.
- Provide integration style tests (SQLite) that cover:
  - passkey registration and login flow state
  - WebAuthn challenge TTL and single use behavior
  - ID generators (length, prefix, charset)
  - last passkey invariant (cannot revoke last active passkey)
  - device registration and revocation
  - token verification behavior (kid lookup, signature verification, aud separation)
  - protected endpoint access based on server side DB authorization
  - password auth lifecycle (when password extra enabled)

E2E (Playwright) should cover:

- passkey registration and login flows in the scaffolded web and api
- device key registration and device signed requests
- passkey management UI for listing and last passkey revoke block
- OpenAPI type generation being usable in the web app

## Docs expectations

- README quickstart must be runnable and minimal.
- Docs must not mention refresh tokens or server minted access tokens unless reintroduced.
- Keep `docs/security/frontend.md` aligned with implementation.

## Commit hygiene for agents

### Required pre commit checks (must run before committing)

Before committing any changes, format the code and run the same checks used in CI (locked mode):

- Format (apply changes):
  - `uv run --locked ruff format .`

- Verify the full CI gate locally:
  - `uv run --locked ruff format --check .`
  - `uv run --locked ruff check .`
  - `uv run --locked mypy src`
  - `uv run --locked pytest -v`

Do not commit code that fails any of the above commands. Fix issues first.

If a design choice is non obvious, add a short note under `docs/decisions/`.

### Frontend template checks

When modifying files under `packages/create-h4ckath0n/templates/fullstack/web/`, run from that
file's directory:

- `npm run lint` (ESLint)
- `npm run typecheck` (tsc, no emit)
- `npm run test` (Vitest)
- `npm run build` (production build)

Do not commit frontend template changes that fail these checks.

### E2E quality guard (required, CI equivalent)

When modifying auth, passkeys, device auth, scaffolding, or OpenAPI type generation:

Run E2E locally in a CI equivalent way (install browsers and deps, then run tests):

- From `packages/create-h4ckath0n/templates/fullstack/web/`:
  - `npm ci`
  - `npm exec --no -- playwright install --with-deps chromium`
  - `npm exec --no -- playwright test`

Ensure it passes before submitting work.

### Scaffold CLI checks

When modifying `packages/create-h4ckath0n/bin/` or `packages/create-h4ckath0n/lib/`:

- Run `node packages/create-h4ckath0n/bin/cli.js --help` to verify CLI syntax.
- Test scaffold output with `node packages/create-h4ckath0n/bin/cli.js test-project --no-install --no-git`
  in a temp directory.
- Ensure the scaffolded project can run web and api checks and E2E.
