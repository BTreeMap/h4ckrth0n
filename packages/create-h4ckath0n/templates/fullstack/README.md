# {{PROJECT_NAME}}

Full-stack hackathon project scaffolded with [h4ckath0n](https://github.com/BTreeMap/h4ckath0n).

## Quick start

```bash
# Start both backend and frontend
cd backend
uv run h4ckath0n dev
```

Backend runs at http://localhost:8000, frontend at http://localhost:5173.

## Structure

```
{{PROJECT_NAME}}/
  backend/    Python (FastAPI + h4ckath0n library)
  web/        React + Vite + TypeScript + Tailwind v4
  .env        Environment variables (gitignored)
```

## Auth model

- Passkeys (WebAuthn) for registration and login
- Each device gets a P-256 keypair (private key non-extractable, stored in IndexedDB)
- API requests use short-lived JWTs (15 min) signed by the device key
- Server verifies JWT signature and enforces RBAC from the database
- No privilege claims in the JWT; all roles/scopes are server-derived

## Development

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

### Frontend

```bash
cd web
npm install
npm run dev
```

### Environment

Copy `.env.example` to `.env` and set values as needed. See the h4ckath0n docs for all configuration options.

## License

MIT
