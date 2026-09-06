# Atlas Journal: Critical Learnings

## 2026-02-28 - API route substring matching is unreliable for drift checks

**Learning:** Checking whether a path string appears *anywhere* in a README causes false negatives
when one route's path is a substring of another (e.g. `/auth/passkeys/{key_id}` inside
`/auth/passkeys/{key_id}/revoke`). The drift check must match `METHOD /path` as a combined token,
ideally inside backtick delimiters, to avoid this trap.

**Action:** Always match method+path together in drift checks. Use `` `METHOD /path` `` patterns
that mirror the actual markdown formatting.
## 2024-05-25 - FastAPI app.routes vs app.openapi()

**Learning:** When programmatically enumerating routes in recent FastAPI versions (0.115+), `app.routes` obscures routes inside `_IncludedRouter`. `app.openapi().get('paths', {})` reliably retrieves all endpoints and metadata.

**Action:** Always use `app.openapi().get('paths', {})` instead of `app.routes` for accurate drift-checking and doc generation.
