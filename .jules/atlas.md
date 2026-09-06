# Atlas Journal: Critical Learnings

## 2026-02-28 - API route substring matching is unreliable for drift checks

**Learning:** Checking whether a path string appears *anywhere* in a README causes false negatives
when one route's path is a substring of another (e.g. `/auth/passkeys/{key_id}` inside
`/auth/passkeys/{key_id}/revoke`). The drift check must match `METHOD /path` as a combined token,
ideally inside backtick delimiters, to avoid this trap.

**Action:** Always match method+path together in drift checks. Use `` `METHOD /path` `` patterns
that mirror the actual markdown formatting.
## 2026-02-28 - FastAPI nested routers hide route details in .routes

**Learning:** In newer FastAPI versions, nested routers appear internally as `_IncludedRouter` within `app.routes`, hiding their `.path` and `.methods` attributes. Iterating over `app.routes` directly (e.g., `for route in app.routes:`) will miss these deeply nested endpoints, leading to incomplete API documentation or false positives in drift checks.
**Action:** To reliably enumerate all fully registered API endpoints for drift checks or documentation generation, always generate and inspect the OpenAPI schema (e.g., `app.openapi().get("paths", {})`) instead of attempting to walk the internal `app.routes` tree.
