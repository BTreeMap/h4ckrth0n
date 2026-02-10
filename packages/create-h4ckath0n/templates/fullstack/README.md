# {{PROJECT_NAME}}

Full-stack hackathon project scaffolded with [h4ckath0n](https://github.com/BTreeMap/h4ckath0n).

## Quick start

```bash
# Start both API and web servers
cd api
uv run h4ckath0n dev
```

API runs at http://localhost:8000, web at http://localhost:5173.

## Structure

```
{{PROJECT_NAME}}/
  api/        Python (FastAPI + h4ckath0n library)
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

### Full-stack (recommended)

```bash
cd web
npm install
npm run dev:fullstack
```

This single command:
1. Starts the backend API server (uvicorn with auto-reload)
2. Waits for the OpenAPI schema to become available
3. Generates TypeScript types from the backend schema (`src/api/generated/`)
4. Watches backend files and regenerates types on changes
5. Starts the Vite dev server

API runs at http://localhost:8000, web at http://localhost:5173.

### API only

```bash
cd api
uv sync
uv run uvicorn app.main:app --reload
```

### Web only

```bash
cd web
npm install
npm run dev
```

### Regenerating API types

If the backend models change, regenerate the typed client (requires backend running):

```bash
cd web
npm run gen:api
```

### Environment

Copy `.env.example` to `.env` and set values as needed. See the h4ckath0n docs for all configuration options.

## License

MIT
