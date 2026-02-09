"""Application factory."""

from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from h4ckrth0n.auth.passkeys.router import passkeys_router, router as passkey_router
from h4ckrth0n.auth.router import router as auth_router
from h4ckrth0n.config import Settings
from h4ckrth0n.db.base import Base
from h4ckrth0n.db.engine import create_engine_from_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure a FastAPI application with auth, DB, and (optionally) observability."""
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="h4ckrth0n",
        description="Hackathon app powered by h4ckrth0n",
        version="0.1.0",
    )

    # --- database ---
    engine = create_engine_from_settings(settings)
    # Import models so they register with Base.metadata before create_all.
    import h4ckrth0n.auth.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)

    # Store on app.state for dependency access.
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory

    # --- routers ---
    # Passkey routes are always mounted (default auth).
    app.include_router(passkey_router)
    app.include_router(passkeys_router)

    # Core auth routes (refresh, logout) are always mounted.
    app.include_router(auth_router)

    # Password routes are only mounted when the extra is installed AND enabled.
    if settings.password_auth_enabled:
        try:
            from h4ckrth0n.auth.router import get_password_router

            app.include_router(get_password_router(), prefix="/auth", tags=["password-auth"])
        except RuntimeError:
            pass  # argon2-cffi not installed

    # --- default routes ---
    @app.get("/")
    def root():  # type: ignore[no-untyped-def]
        return {"message": "Welcome to your h4ckrth0n app!"}

    @app.get("/health")
    def health():  # type: ignore[no-untyped-def]
        return {"status": "healthy"}

    return app
