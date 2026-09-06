## 2024-09-04 - Generate API Routes via OpenAPI Paths
**Learning:** Hand-written lists of API routes quickly become outdated as endpoints (e.g. for Auth/Passkeys and Passwords) are added or removed.
**Action:** Use `app.openapi().get("paths", {})` to generate exact route documentation wrapped in HTML comments (`<!-- BEGIN ROUTES -->`), enforcing an automated drift-prevention script to verify equality.
