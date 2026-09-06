# Atlas Journal: Critical Learnings

## 2026-02-28 - API route substring matching is unreliable for drift checks

**Learning:** Checking whether a path string appears *anywhere* in a README causes false negatives
when one route's path is a substring of another (e.g. `/auth/passkeys/{key_id}` inside
`/auth/passkeys/{key_id}/revoke`). The drift check must match `METHOD /path` as a combined token,
ideally inside backtick delimiters, to avoid this trap.

**Action:** Always match method+path together in drift checks. Use `` `METHOD /path` `` patterns
that mirror the actual markdown formatting.

## 2026-02-28 - FastAPI app.routes obfuscates _IncludedRouter endpoints
**Learning:** In recent versions of FastAPI (e.g. 0.115+), `app.routes` obfuscates endpoints that are nested within `_IncludedRouter`. Iterating over `app.routes` directly and checking for `.methods` and `.path` will miss these routes and lead to false negatives in drift checks.
**Action:** When programmatically enumerating API routes for drift prevention or similar scripts, use `app.openapi().get("paths", {})` instead of manually iterating over `app.routes` to reliably capture all nested endpoints and their metadata.
