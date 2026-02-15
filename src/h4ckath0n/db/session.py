"""Session dependency for FastAPI."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker


def get_db_dependency(session_factory: sessionmaker) -> Any:  # noqa: ANN401
    """Return a FastAPI ``Depends``-compatible generator."""

    def _get_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    return _get_db


def get_async_db_dependency(
    session_factory: async_sessionmaker[AsyncSession],
) -> Any:  # noqa: ANN401
    """Return a FastAPI ``Depends``-compatible async generator."""

    async def _get_async_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    return _get_async_db


# Convenience alias – populated at app startup by create_app.
get_db = get_db_dependency
