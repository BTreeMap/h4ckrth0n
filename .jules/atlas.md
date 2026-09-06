# Atlas Journal: Critical Learnings

## 2026-02-28 - API route substring matching is unreliable for drift checks

**Learning:** Checking whether a path string appears *anywhere* in a README causes false negatives
when one route's path is a substring of another (e.g. `/auth/passkeys/{key_id}` inside
`/auth/passkeys/{key_id}/revoke`). The drift check must match `METHOD /path` as a combined token,
ideally inside backtick delimiters, to avoid this trap.

**Action:** Always match method+path together in drift checks. Use `` `METHOD /path` `` patterns
that mirror the actual markdown formatting.

## 2026-02-28 - OpenAPI parsing is more reliable than internal router inspection

**Learning:** In FastAPI, nested routers can obscure endpoint paths and methods when traversing `app.routes`. Parsing the generated OpenAPI schema is a much more robust and complete way to extract all API endpoints.

**Action:** When extracting routes for documentation or drift checks, always generate the OpenAPI schema and parse it instead of traversing `app.routes`.
