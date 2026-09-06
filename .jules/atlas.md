# Atlas Journal: Critical Learnings

## 2026-02-28 - API route substring matching is unreliable for drift checks

**Learning:** Checking whether a path string appears *anywhere* in a README causes false negatives
when one route's path is a substring of another (e.g. `/auth/passkeys/{key_id}` inside
`/auth/passkeys/{key_id}/revoke`). The drift check must match `METHOD /path` as a combined token,
ideally inside backtick delimiters, to avoid this trap.

**Action:** Always match method+path together in drift checks. Use `` `METHOD /path` `` patterns
that mirror the actual markdown formatting.

## 2026-02-28 - FastAPI 0.115+ sub-router drift and README generation

**Learning:** In recent versions of FastAPI, `app.routes` obscures endpoints registered via `app.include_router()` by wrapping them in `_IncludedRouter` objects. Additionally, maintaining hand-written API endpoint lists in the `README.md` is highly prone to drift.

**Action:** When programmatically discovering routes for drift-prevention scripts, always parse the generated OpenAPI schema using `app.openapi().get("paths", {})` rather than iterating through `app.routes`. To prevent `README.md` drift, use standard delimiter markers (e.g., `<!-- BEGIN API ROUTES -->`) and dynamically generate the API endpoints markdown table directly from the OpenAPI schema.
