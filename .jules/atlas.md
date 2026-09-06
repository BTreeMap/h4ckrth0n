# Atlas Journal: Critical Learnings

## 2026-02-28 - API route substring matching is unreliable for drift checks

**Learning:** Checking whether a path string appears *anywhere* in a README causes false negatives
when one route's path is a substring of another (e.g. `/auth/passkeys/{key_id}` inside
`/auth/passkeys/{key_id}/revoke`). The drift check must match `METHOD /path` as a combined token,
ideally inside backtick delimiters, to avoid this trap.

**Action:** Always match method+path together in drift checks. Use `` `METHOD /path` `` patterns
that mirror the actual markdown formatting.

## 2026-03-01 - Hidden nested routes in drift-prevention checks

**Learning:** In recent versions of FastAPI, `app.routes` obfuscates endpoints nested within `_IncludedRouter`, leading to false negatives (i.e. skipped validations) in drift-prevention scripts.
**Action:** When enumerating routes programmatically to catch drift, iterate through `app.openapi().get("paths", {})` instead of `app.routes` to reliably capture all endpoints.
