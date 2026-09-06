# Atlas Journal: Critical Learnings

## 2026-02-28 - API route substring matching is unreliable for drift checks

**Learning:** Checking whether a path string appears *anywhere* in a README causes false negatives
when one route's path is a substring of another (e.g. `/auth/passkeys/{key_id}` inside
`/auth/passkeys/{key_id}/revoke`). The drift check must match `METHOD /path` as a combined token,
ideally inside backtick delimiters, to avoid this trap.

**Action:** Always match method+path together in drift checks. Use `` `METHOD /path` `` patterns
that mirror the actual markdown formatting.

## 2026-03-01 - OpenAPI generation over internal app.routes matching
**Learning:** In FastAPI apps (v0.115+), nested routers are represented internally as `_IncludedRouter` within `app.routes`, hiding `.path` and `.methods`. To reliably enumerate all fully registered API endpoints (e.g., for drift checks or docs generation), generate and inspect the OpenAPI schema via `app.openapi().get('paths', {})` rather than attempting to recursively walk the internal routing tree.
**Action:** Replace manual API route parsing with OpenAPI schema parsing for route drift detection.
