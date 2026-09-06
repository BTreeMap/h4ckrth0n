# Atlas Journal: Critical Learnings

## 2026-02-28 - API route substring matching is unreliable for drift checks

**Learning:** Checking whether a path string appears *anywhere* in a README causes false negatives
when one route's path is a substring of another (e.g. `/auth/passkeys/{key_id}` inside
`/auth/passkeys/{key_id}/revoke`). The drift check must match `METHOD /path` as a combined token,
ideally inside backtick delimiters, to avoid this trap.

**Action:** Always match method+path together in drift checks. Use `` `METHOD /path` `` patterns
that mirror the actual markdown formatting.

## 2026-03-01 - Generating OpenAPI route tables prevents missing nested routes

**Learning:** Checking against `app.routes` misses routes mounted inside an `_IncludedRouter` (default behavior in FastAPI v0.115+), which can cause drift checks to falsely pass while missing the majority of routes. Generating markdown dynamically from `app.openapi().get("paths", {})` is both more accurate and completely removes the need for hand-maintained lists in README.md.

**Action:** Consolidate multiple API route lists in markdown by injecting generated markdown tables bounded by `<!-- BEGIN API ROUTES -->` markers. Ensure the drift check tool both enforces and fixes the synchronization using the OpenAPI schema.
