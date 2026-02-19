# h4ckath0n

Ship hackathon products fast with a secure FastAPI bootstrap and passkey-first authentication.

## What you get

- FastAPI app factory with passkey routes mounted by default
- Device signed ES256 JWT authentication and server-side RBAC (user, admin, scopes)
- SQLAlchemy 2.x models with automatic table creation on startup
- LLM wrapper around the OpenAI SDK with timeouts and retries
- Optional password auth extra for email and password flows
- Optional Redis extra that only adds the dependency, no integration is provided yet
- Trace ID middleware and LangSmith environment wiring via `init_observability`
- Full stack scaffold CLI that produces an API and web template

## Installation

### Recommended (uv)

```bash
uv add h4ckath0n
```

Optional extras:

```bash
uv add "h4ckath0n[password]"  # Argon2 based password auth
uv add "h4ckath0n[redis]"     # Redis dependency only
```

### pip

```bash
pip install h4ckath0n
```

## Scaffold a full stack project

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

## OpenAPI docs

- Interactive docs live at `/docs` when the app is running.
- Public routes like passkey start and finish work without auth.
- Protected routes require an `Authorization: Bearer <device_jwt>` header that the web
  template can mint after login.

## Auth model

### Passkeys by default

The default authentication path uses passkeys (WebAuthn). The core flows are:

1. `POST /auth/passkey/register/start` and `POST /auth/passkey/register/finish`
2. `POST /auth/passkey/login/start` and `POST /auth/passkey/login/finish`
3. `POST /auth/passkey/add/start` and `POST /auth/passkey/add/finish` for adding devices
4. `GET /auth/passkeys` and `POST /auth/passkeys/{key_id}/revoke` for management

### Device signed JWTs

After login or registration, the client binds a device key and mints short lived ES256
JWTs. The server uses the `kid` header to load the device public key and verifies the
signature and `aud` claim. JWTs contain only identity and time claims, no roles or
scopes.

### ID scheme

- User IDs are 32 characters and start with `u`
- Passkey IDs are 32 characters and start with `k`
- Device IDs are 32 characters and start with `d`
- Password reset tokens use UUID hex, not the base32 scheme

## Secure endpoint protection

```python
from h4ckath0n import create_app
from h4ckath0n.auth import require_user

app = create_app()

@app.get("/me")
def me(user=require_user()):
    return {"id": user.id, "role": user.role}
```

Admin only endpoint:

```python
from h4ckath0n.auth import require_admin

@app.get("/admin/dashboard")
def admin_dashboard(user=require_admin()):
    return {"ok": True}
```

Scoped permissions:

```python
from h4ckath0n.auth import require_scopes

@app.post("/billing/refund")
def refund(user=require_scopes("billing:refund")):
    return {"status": "queued"}
```

## Password auth (optional)

Password routes mount only when the password extra is installed and
`H4CKATH0N_PASSWORD_AUTH_ENABLED=true`.

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/password-reset/request`
- `POST /auth/password-reset/confirm`

Password auth is only an identity bootstrap. It binds a device key but does not return
access tokens, refresh tokens, or cookies.

## Configuration

All settings use the `H4CKATH0N_` prefix unless noted.

| Variable | Default | Description |
|---|---|---|
| `H4CKATH0N_ENV` | `development` | `development` or `production` |
| `H4CKATH0N_DATABASE_URL` | `sqlite:///./h4ckath0n.db` | SQLAlchemy connection string |
| `H4CKATH0N_AUTO_UPGRADE` | `false` | Auto-run packaged DB migrations to head on startup |
| `H4CKATH0N_RP_ID` | `localhost` in development | WebAuthn relying party ID, required in production |
| `H4CKATH0N_ORIGIN` | `http://localhost:8000` in development | WebAuthn origin, required in production |
| `H4CKATH0N_WEBAUTHN_TTL_SECONDS` | `300` | WebAuthn challenge TTL in seconds |
| `H4CKATH0N_USER_VERIFICATION` | `preferred` | WebAuthn user verification requirement |
| `H4CKATH0N_ATTESTATION` | `none` | WebAuthn attestation preference |
| `H4CKATH0N_PASSWORD_AUTH_ENABLED` | `false` | Enable password routes when the extra is installed |
| `H4CKATH0N_PASSWORD_RESET_EXPIRE_MINUTES` | `30` | Password reset token expiry in minutes |
| `H4CKATH0N_BOOTSTRAP_ADMIN_EMAILS` | `[]` | JSON list of emails that become admin on password signup |
| `H4CKATH0N_FIRST_USER_IS_ADMIN` | `false` | First password signup becomes admin |
| `OPENAI_API_KEY` | empty | OpenAI API key for the LLM wrapper |
| `H4CKATH0N_OPENAI_API_KEY` | empty | Alternate OpenAI API key for the LLM wrapper |

In development, missing `RP_ID` and `ORIGIN` fall back to localhost defaults with
warnings. In production, missing values raise a runtime error when passkey flows start.

## Postgres readiness and migrations

Set a Postgres database URL to run against Postgres:

```
H4CKATH0N_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname
```

`create_app()` calls `Base.metadata.create_all` on startup.

h4ckath0n also ships an operator CLI and packaged Alembic migrations:

```bash
h4ckath0n db ping
h4ckath0n db migrate upgrade --to head --yes
```

If startup or `db ping` reports that the database schema is behind, run:

```bash
h4ckath0n db migrate upgrade --to head --yes
```

If startup or `db ping` reports that the database was initialized without Alembic versioning,
run:

```bash
h4ckath0n db migrate stamp --to <baseline> --yes
h4ckath0n db migrate upgrade --to head --yes
```

For legacy `create_all` deployments in current releases, use `<baseline>=head`.

## LLM usage

```python
from h4ckath0n.llm import llm

client = llm()
resp = client.chat(
    system="You are a helpful assistant.",
    user="Summarize this in one sentence: ...",
)
print(resp.text)
```

The wrapper raises a `RuntimeError` if no API key is configured.

## Observability

`init_observability(app)` adds an `X-Trace-Id` header to responses and can set
LangSmith environment variables if `ObservabilitySettings.langsmith_tracing` is true.
It does not instrument FastAPI, LangChain, or OpenAI calls by itself.

```python
from h4ckath0n import create_app
from h4ckath0n.obs import ObservabilitySettings, init_observability

app = create_app()
init_observability(app, ObservabilitySettings(langsmith_tracing=True))
```

## Compatibility and operational notes

- Passkeys require HTTPS in production. `localhost` is allowed for development.
- `H4CKATH0N_RP_ID` must match your production domain and `H4CKATH0N_ORIGIN` must
  include the scheme and host.
- The last active passkey cannot be revoked. Add a second passkey first.

## Development

```bash
git clone https://github.com/BTreeMap/h4ckath0n.git
cd h4ckath0n
uv sync --locked --all-extras
```

Quality gates:

```bash
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked mypy src
uv run --locked pytest -v
```

## License

MIT. See `LICENSE`.
