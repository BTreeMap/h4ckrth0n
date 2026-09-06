## 2023-10-24 - Drift-prevention with OpenAPI
**Learning:** `app.routes` in FastAPI masks routes within nested `APIRouter` objects (represented as `_IncludedRouter`). Manually inspecting `app.routes` led to silently ignoring most of the API in the drift check script.
**Action:** Always parse the generated `app.openapi()["paths"]` instead of raw `app.routes` when creating drift-prevention checks for API endpoints in FastAPI. Ensure drift-check scripts include a `--fix` flag to automatically update the markdown utilizing `<!-- BEGIN ... -->` and `<!-- END ... -->` structural markers.
