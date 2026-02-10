# h4ckath0n

Ship hackathon products fast, with secure-by-default auth, RBAC, Postgres readiness, and built-in LLM tooling.

**h4ckath0n** is an opinionated Python library that makes it hard to accidentally ship insecure glue code during a hackathon.

## What you get by default

- **API**: FastAPI app bootstrap with OpenAPI docs
- **Auth**: passkey (WebAuthn) registration and login – no passwords required
- **AuthZ**: built-in RBAC with `user` and `admin` roles, plus scoped permissions via JWT claims
- **Database**: SQLAlchemy 2.x + Alembic, works with SQLite (zero-config dev) and Postgres (recommended for production)
- **LLM**: built-in LLM client wrapper (OpenAI SDK) with safe defaults and redaction hooks
- **Observability**: opt-in LangSmith / OpenTelemetry tracing with trace ID propagation
- **Config**: environment-driven settings via pydantic-settings

Password auth and Redis-based queues/caching are available as optional extras.

## Installation

### Recommended (uv)

```bash
uv add h4ckath0n
```

Optional extras:

```bash
uv add "h4ckath0n[password]"  # Argon2-based password auth (off by default)
uv add "h4ckath0n[redis]"     # Redis support
```

### pip

```bash
pip install h4ckath0n
```

## Scaffold a full-stack project

```bash
npx h4ckath0n my-app
```

## Quickstart

```python
from h4ckath0n import create_app

app = create_app()
```

Run:

```bash
uv run uvicorn your_module:app --reload
```

Open docs at `/docs` (Swagger UI). Passkey auth routes are mounted automatically.

## Auth: passkeys by default

h4ckath0n uses **passkeys (WebAuthn)** as the default authentication method. No passwords, no email required.

### How it works

1. **Register**: `POST /auth/passkey/register/start` → browser creates a passkey → `POST /auth/passkey/register/finish` → account created, tokens returned.
2. **Login**: `POST /auth/passkey/login/start` → browser signs with passkey → `POST /auth/passkey/login/finish` → tokens returned. Username-less by default.
3. **Add passkey**: authenticated users can add more passkeys via `POST /auth/passkey/add/start` + `POST /auth/passkey/add/finish`.
4. **Revoke passkey**: `POST /auth/passkeys/{key_id}/revoke` – but **cannot revoke the last active passkey** (returns `LAST_PASSKEY` error).

### ID scheme

- User IDs: 32-char base32 string starting with `u` (e.g., `u3mfgh7k2n4p5q6r7s8t9v0w1x2y3z4a`)
- Internal key IDs: 32-char base32 string starting with `k`
- The browser's WebAuthn `credentialId` is stored separately and used for signature verification.

## Secure-by-default endpoint protection

Protect an endpoint (requires a logged-in user):

```python
from h4ckath0n import create_app
from h4ckath0n.auth import require_user

app = create_app()

@app.get("/me")
def me(user=require_user()):
    return {"id": user.id, "role": user.role}
```

Admin-only endpoint:

```python
from h4ckath0n.auth import require_admin

@app.get("/admin/dashboard")
def admin_dashboard(user=require_admin()):
    return {"ok": True}
```

Scoped privileges (JWT claim `scopes`):

```python
from h4ckath0n.auth import require_scopes

@app.post("/billing/refund")
def refund(user=require_scopes("billing:refund")):
    return {"status": "queued"}
```

## Auth routes

h4ckath0n mounts these routes by default:

### Passkey (default)

- `POST /auth/passkey/register/start` – begin passkey registration (creates account)
- `POST /auth/passkey/register/finish` – complete registration (returns access + refresh tokens)
- `POST /auth/passkey/login/start` – begin passkey login (username-less)
- `POST /auth/passkey/login/finish` – complete login (returns access + refresh tokens)
- `POST /auth/passkey/add/start` – begin adding a passkey (authenticated)
- `POST /auth/passkey/add/finish` – complete adding a passkey (authenticated)
- `GET /auth/passkeys` – list current user's passkeys (authenticated)
- `POST /auth/passkeys/{key_id}/revoke` – revoke a passkey (authenticated, blocked if last)

### Token management

- `POST /auth/refresh` – rotate refresh token, get new access token
- `POST /auth/logout` – revoke refresh token

### Password auth (optional extra)

Only available when `h4ckath0n[password]` is installed AND `H4CKATH0N_PASSWORD_AUTH_ENABLED=true`:

- `POST /auth/register` – create account with email + password
- `POST /auth/login` – authenticate with email + password
- `POST /auth/password-reset/request` – request password reset
- `POST /auth/password-reset/confirm` – confirm password reset

## Database

Zero-config default: SQLite is used if no database URL is provided.

To use Postgres (recommended for production):

```
H4CKATH0N_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname
```

The `psycopg[binary]` driver is included by default – no extra install needed.

## LLM

h4ckath0n includes LLM tooling by default. Set `OPENAI_API_KEY` and use:

```python
from h4ckath0n.llm import llm

client = llm()
resp = client.chat(
    system="You are a helpful assistant.",
    user="Summarize this in one sentence: ...",
)
print(resp.text)
```

Fails gracefully with a clear error message when `OPENAI_API_KEY` is not set.

## Configuration

Everything is environment-driven (prefix `H4CKATH0N_`):

| Variable | Default | Description |
|---|---|---|
| `H4CKATH0N_ENV` | `development` | `development` or `production` |
| `H4CKATH0N_DATABASE_URL` | `sqlite:///./h4ckath0n.db` | Database connection string |
| `H4CKATH0N_AUTH_SIGNING_KEY` | *(ephemeral in dev)* | JWT signing key (**required in production**) |
| `H4CKATH0N_RP_ID` | `localhost` *(dev only)* | WebAuthn relying party ID (**required in production**) |
| `H4CKATH0N_ORIGIN` | `http://localhost:8000` *(dev only)* | WebAuthn expected origin (**required in production**) |
| `H4CKATH0N_WEBAUTHN_TTL_SECONDS` | `300` | Challenge expiry time (seconds) |
| `H4CKATH0N_USER_VERIFICATION` | `preferred` | WebAuthn user verification requirement |
| `H4CKATH0N_ATTESTATION` | `none` | WebAuthn attestation preference |
| `H4CKATH0N_PASSWORD_AUTH_ENABLED` | `false` | Enable password auth routes (requires `[password]` extra) |
| `H4CKATH0N_BOOTSTRAP_ADMIN_EMAILS` | `[]` | JSON list of emails that get admin role on registration |
| `H4CKATH0N_FIRST_USER_IS_ADMIN` | `false` | First registered user becomes admin (dev convenience) |
| `OPENAI_API_KEY` | — | OpenAI API key for the LLM module |

In development mode, missing signing keys and WebAuthn settings generate ephemeral/localhost defaults with warnings.
In production mode, missing critical secrets and `RP_ID`/`ORIGIN` cause a hard error.

## Observability (opt-in)

Enable end-to-end tracing across FastAPI requests, LangGraph nodes, tool calls, and LLM calls.

### Enable LangSmith tracing

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=your-project-name
```

### Trace IDs

When observability is enabled, h4ckath0n attaches `X-Trace-Id` to all responses:

```python
from h4ckath0n import create_app
from h4ckath0n.obs import init_observability

app = create_app()
init_observability(app)
```

## Development

```bash
git clone https://github.com/BTreeMap/h4ckath0n.git
cd h4ckath0n
uv sync
uv run pytest
```

Quality gates:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
```

Build:

```bash
uv build
```

## License

MIT. See `LICENSE`.
