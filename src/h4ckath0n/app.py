"""Application factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import async_sessionmaker

from h4ckath0n.auth.passkeys.router import passkeys_router
from h4ckath0n.auth.passkeys.router import router as passkey_router
from h4ckath0n.config import Settings
from h4ckath0n.db.base import Base
from h4ckath0n.db.engine import create_async_engine_from_settings
from h4ckath0n.version import __version__ as H4CKATH0N_VERSION


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure a FastAPI application with auth, DB, and (optionally) observability."""
    if settings is None:
        settings = Settings()

    # --- database (async) ---
    async_engine = create_async_engine_from_settings(settings)

    # Import models so they register with Base.metadata before create_all.
    import h4ckath0n.auth.models  # noqa: F401

    async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield
        await async_engine.dispose()

    app = FastAPI(
        title="h4ckath0n",
        description="Hackathon app powered by h4ckath0n",
        version=H4CKATH0N_VERSION,
        lifespan=lifespan,
    )

    # Store on app.state for dependency access.
    app.state.settings = settings
    app.state.async_engine = async_engine
    app.state.async_session_factory = async_session_factory

    # --- routers ---
    # Passkey routes are always mounted (default auth).
    app.include_router(passkey_router)
    app.include_router(passkeys_router)

    # Password routes are only mounted when the extra is installed AND enabled.
    if settings.password_auth_enabled:
        try:
            from h4ckath0n.auth.router import get_password_router

            app.include_router(get_password_router(), prefix="/auth", tags=["password-auth"])
        except RuntimeError:
            pass  # argon2-cffi not installed

    # --- default routes ---
    class RootResponse(BaseModel):
        message: str = Field(..., description="Welcome message.")

    class HealthResponse(BaseModel):
        status: str = Field(..., description="Health status string.")

    @app.get(
        "/",
        response_model=RootResponse,
        summary="Welcome",
        description="Default root route provided by h4ckath0n.",
    )
    def root() -> RootResponse:
        return RootResponse(message="Welcome to your h4ckath0n app!")

    @app.get(
        "/health",
        response_model=HealthResponse,
        summary="Health",
        description="Basic health check for the app.",
    )
    def health() -> HealthResponse:
        return HealthResponse(status="healthy")

    return app
