# Atlas Journal: Critical Learnings

## 2026-02-28 - API route substring matching is unreliable for drift checks

**Learning:** Checking whether a path string appears *anywhere* in a README causes false negatives
when one route's path is a substring of another (e.g. `/auth/passkeys/{key_id}` inside
`/auth/passkeys/{key_id}/revoke`). The drift check must match `METHOD /path` as a combined token,
ideally inside backtick delimiters, to avoid this trap.

**Action:** Always match method+path together in drift checks. Use `` `METHOD /path` `` patterns
that mirror the actual markdown formatting.
## 2024-05-18 - Nested Router Drift
**Learning:** The existing script `check_doc_routes.py` enumerated endpoints by directly iterating over `app.routes`. This missed nested router endpoints from `_IncludedRouter` leading to severe documentation drift where only 2 routes were detected out of 25 actual endpoints.
**Action:** Always fetch API routes by introspecting the OpenAPI schema (`app.openapi().get("paths", {})`) rather than iterating `app.routes`.
