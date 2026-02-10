"""Session dependency for FastAPI."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

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


# Convenience alias – populated at app startup by create_app.
get_db = get_db_dependency
