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
from sqlalchemy import inspect
from sqlalchemy.engine import Engine, create_engine, make_url


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

    import h4ckath0n.auth.models  # noqa: F401
    from h4ckath0n.db.base import Base

    engine = create_sync_engine(sync_url)
    try:
        with engine.connect() as conn:
            inspector = inspect(conn)
            table_names = set(inspector.get_table_names())
            has_alembic = "alembic_version" in table_names

            if has_alembic:
                migration_ctx = MigrationContext.configure(conn)
                current_revisions = tuple(sorted(migration_ctx.get_current_heads()))
            else:
                current_revisions = tuple()

        h4_tables = set(Base.metadata.tables.keys())
        has_h4_tables = bool(h4_tables & table_names)
    finally:
        engine.dispose()

    if current_revisions and set(current_revisions) == set(head_revisions):
        return SchemaStatus(
            state="at_head",
            current_revisions=current_revisions,
            head_revisions=head_revisions,
            warning=None,
        )

    if not current_revisions and has_h4_tables:
        return SchemaStatus(
            state="stamp_required",
            current_revisions=current_revisions,
            head_revisions=head_revisions,
            warning=(
                "database appears initialized without alembic versioning; "
                "run h4ckath0n db migrate stamp --to <baseline> --yes "
                "(for current releases, use <baseline>=head), then "
                "h4ckath0n db migrate upgrade --to head --yes"
            ),
        )

    if not current_revisions and not has_h4_tables:
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
    """Upgrade schema to head using packaged migrations.

    For a fresh database, initialize schema with create_all and stamp head.
    """
    sync_url = normalize_db_url_for_sync(db_url)
    status = get_schema_status(sync_url)
    if status.state == "stamp_required":
        return status

    with packaged_migrations_dir() as migrations_dir:
        cfg = _alembic_config(sync_url, migrations_dir)
        if status.state == "fresh":
            import h4ckath0n.auth.models  # noqa: F401
            from h4ckath0n.db.base import Base

            engine = create_sync_engine(sync_url)
            try:
                Base.metadata.create_all(engine)
            finally:
                engine.dispose()
            alembic_command.stamp(cfg, "head")
        else:
            alembic_command.upgrade(cfg, "head")

    return get_schema_status(sync_url)


def run_upgrade_to_head(db_url: str) -> SchemaStatus:
    """Backwards-compatible sync entrypoint for tooling auto-upgrade."""
    return run_upgrade_to_head_sync(db_url)


async def run_upgrade_to_head_async(db_url: str) -> SchemaStatus:
    """Run sync Alembic upgrade work in a thread when called from async code."""
    sync_url = normalize_db_url_for_sync(db_url)
    return await asyncio.to_thread(run_upgrade_to_head_sync, sync_url)
