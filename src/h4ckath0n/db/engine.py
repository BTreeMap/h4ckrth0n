"""Engine factory."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from h4ckath0n.config import Settings


def create_engine_from_settings(settings: Settings | None = None) -> Engine:
    """Create a SQLAlchemy engine from application settings."""
    if settings is None:
        settings = Settings()
    url = settings.database_url
    connect_args: dict = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


def _sync_to_async_url(url: str) -> str:
    """Convert a sync database URL to its async equivalent."""
    if url.startswith("sqlite:"):
        return url.replace("sqlite:", "sqlite+aiosqlite:", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def create_async_engine_from_settings(settings: Settings | None = None) -> AsyncEngine:
    """Create a SQLAlchemy async engine from application settings."""
    if settings is None:
        settings = Settings()
    url = _sync_to_async_url(settings.database_url)
    connect_args: dict = {}
    if "sqlite" in url:
        connect_args["check_same_thread"] = False
    kwargs: dict = {"connect_args": connect_args}
    if "postgresql" in url or "asyncpg" in url:
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
        kwargs["pool_pre_ping"] = True
    return create_async_engine(url, **kwargs)
