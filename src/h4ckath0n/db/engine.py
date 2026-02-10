"""Engine factory."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine

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
