"""Application entry point."""

from app.middleware import add_csp_middleware
from h4ckath0n import create_app

app = create_app()
add_csp_middleware(app)
