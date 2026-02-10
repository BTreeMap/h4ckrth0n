"""Application entry point."""

from app.middleware import add_csp_middleware
from h4ckath0n import create_app

app = create_app()
add_csp_middleware(app)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Readiness check for E2E and deployment probes."""
    return {"status": "ok"}
