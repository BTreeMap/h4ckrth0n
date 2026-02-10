"""Application entry point."""

from pydantic import BaseModel

from app.middleware import add_csp_middleware
from h4ckath0n import create_app

app = create_app()
add_csp_middleware(app)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Readiness check for E2E and deployment probes."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Demo endpoints – prove that user-defined routes appear in the OpenAPI spec
# and can be consumed by the generated TypeScript client.
# ---------------------------------------------------------------------------


class PingResponse(BaseModel):
    ok: bool


class EchoRequest(BaseModel):
    message: str


class EchoResponse(BaseModel):
    message: str
    reversed: str


@app.get("/demo/ping", tags=["demo"])
def demo_ping() -> PingResponse:
    """Simple liveness ping for the demo namespace."""
    return PingResponse(ok=True)


@app.post("/demo/echo", tags=["demo"])
def demo_echo(body: EchoRequest) -> EchoResponse:
    """Echo back the message along with its reverse."""
    return EchoResponse(message=body.message, reversed=body.message[::-1])
