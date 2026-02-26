"""Runtime helpers for packaged Alembic migrations."""

from __future__ import annotations

import asyncio
import importlib.resources
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from alembic import command as alembic_command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Engine, create_engine, make_url

# Must match env.py
VERSION_TABLE = "h4ckath0n_alembic_version"


class PackagedMigrationsError(RuntimeError):
    """Raised when packaged migrations cannot be found."""


@dataclass(frozen=True)
class SchemaStatus:
    state: str
    current_revisions: tuple[str, ...]
    head_revisions: tuple[str, ...]
    warning: str | None


_ASYNCPG_ONLY_QUERY_KEYS = frozenset(
    {
        "prepared_statement_cache_size",
        "prepared_statement_name_func",
    }
)


def normalize_db_url_for_sync(url: str) -> str:
    """Normalize tooling DB URLs to sync drivers (Alembic env.py is sync-only)."""
    parsed = make_url(url)
    drivername = parsed.drivername
    normalized_driver = drivername

    if drivername == "sqlite+aiosqlite":
        normalized_driver = "sqlite"
    elif drivername == "postgresql+asyncpg" or drivername in {"postgresql", "postgres"}:
        normalized_driver = "postgresql+psycopg"

    query = dict(parsed.query)
    if normalized_driver == "postgresql+psycopg":
        for key in _ASYNCPG_ONLY_QUERY_KEYS:
            query.pop(key, None)

    normalized = parsed.set(drivername=normalized_driver, query=query)
    return normalized.render_as_string(
        hide_password=False
    )  # Alembic needs the password for stamp/upgrades when no env var is used


def create_sync_engine(url: str) -> Engine:
    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


@contextmanager
def packaged_migrations_dir():  # type: ignore[no-untyped-def]
    resources = importlib.resources.files("h4ckath0n.db.migrations")
    with importlib.resources.as_file(resources) as root:
        env_py = root / "env.py"
        versions = root / "versions"
        if not env_py.is_file() or not versions.is_dir():
            raise PackagedMigrationsError(
                "packaged migrations not found; installation may be broken"
            )
        yield root


def _alembic_config(db_url: str, migrations_dir: Path) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(migrations_dir))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def get_schema_status(db_url: str) -> SchemaStatus:
    sync_url = normalize_db_url_for_sync(db_url)
    with packaged_migrations_dir() as migrations_dir:
        cfg = _alembic_config(sync_url, migrations_dir)
        script = ScriptDirectory.from_config(cfg)
        head_revisions = tuple(sorted(script.get_heads()))

    engine = create_sync_engine(sync_url)
    try:
        with engine.connect() as conn:
            # Check for version table
            migration_ctx = MigrationContext.configure(conn, opts={"version_table": VERSION_TABLE})
            current_revisions = tuple(sorted(migration_ctx.get_current_heads()))

    finally:
        engine.dispose()

    if current_revisions and set(current_revisions) == set(head_revisions):
        return SchemaStatus(
            state="at_head",
            current_revisions=current_revisions,
            head_revisions=head_revisions,
            warning=None,
        )

    if not current_revisions:
        # We assume fresh if no version table exists.
        # If tables exist but no version table, Alembic will fail on upgrade anyway,
        # which is the desired "breaking change" behavior (no implicit stamping).
        return SchemaStatus(
            state="fresh",
            current_revisions=current_revisions,
            head_revisions=head_revisions,
            warning=None,
        )

    return SchemaStatus(
        state="behind",
        current_revisions=current_revisions,
        head_revisions=head_revisions,
        warning=(
            "database schema revision is behind code migrations; "
            f"current={list(current_revisions)} head={list(head_revisions)}. "
            "run: h4ckath0n db migrate upgrade --to head --yes"
        ),
    )


def run_upgrade_to_head_sync(db_url: str) -> SchemaStatus:
    """Upgrade schema to head using packaged migrations."""
    sync_url = normalize_db_url_for_sync(db_url)
    # We no longer check for stamp_required or try to fix legacy DBs.

    with packaged_migrations_dir() as migrations_dir:
        cfg = _alembic_config(sync_url, migrations_dir)
        # Always run upgrade. If tables exist and conflict, Alembic raises error.
        alembic_command.upgrade(cfg, "head")

    return get_schema_status(sync_url)


def run_upgrade_to_head(db_url: str) -> SchemaStatus:
    """Backwards-compatible sync entrypoint for tooling auto-upgrade."""
    return run_upgrade_to_head_sync(db_url)


async def run_upgrade_to_head_async(db_url: str) -> SchemaStatus:
    """Run sync Alembic upgrade work in a thread when called from async code."""
    sync_url = normalize_db_url_for_sync(db_url)
    return await asyncio.to_thread(run_upgrade_to_head_sync, sync_url)
