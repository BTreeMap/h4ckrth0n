"""Tests for migration runtime status detection and startup auto-upgrade behavior."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine, text

from h4ckath0n.app import create_app
from h4ckath0n.config import Settings
from h4ckath0n.db.base import Base
from h4ckath0n.db.migrations.runtime import (
    SchemaStatus,
    get_schema_status,
    normalize_db_url_for_sync,
    run_upgrade_to_head_async,
    run_upgrade_to_head_sync,
)


class TestMigrationStatusDetection:
    def test_current_equals_head_no_warning(self, tmp_path):
        db_url = f"sqlite:///{tmp_path}/at_head.db"
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
                )
                conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('0001')"))
            status = get_schema_status(db_url)
            assert status.state == "at_head"
            assert status.warning is None
        finally:
            engine.dispose()

    def test_current_behind_warns(self, tmp_path):
        db_url = f"sqlite:///{tmp_path}/behind.db"
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
                )
                conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('0000')"))
            status = get_schema_status(db_url)
            assert status.state == "behind"
            assert status.warning is not None
            assert "h4ckath0n db migrate upgrade --to head --yes" in status.warning
        finally:
            engine.dispose()

    def test_no_alembic_version_with_tables_warns_stamp_required(self, tmp_path):
        db_url = f"sqlite:///{tmp_path}/stamp_required.db"
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        try:
            import h4ckath0n.auth.models  # noqa: F401

            Base.metadata.create_all(engine)
            status = get_schema_status(db_url)
            assert status.state == "stamp_required"
            assert status.warning is not None
            assert "h4ckath0n db migrate stamp --to <baseline> --yes" in status.warning
        finally:
            engine.dispose()


class TestAutoUpgradeStartup:
    def test_auto_upgrade_runs_on_startup(self, tmp_path):
        db_url = f"sqlite:///{tmp_path}/auto_upgrade.db"
        settings = Settings(database_url=db_url, auto_upgrade=True)
        with patch("h4ckath0n.app.run_upgrade_to_head") as mock_upgrade:
            app = create_app(settings)
            with patch("h4ckath0n.app.get_schema_status") as mock_status:
                mock_status.return_value.warning = None
                with patch("h4ckath0n.app.Base.metadata.create_all"):
                    # Trigger lifespan startup/shutdown.
                    from fastapi.testclient import TestClient

                    with TestClient(app):
                        pass
            mock_upgrade.assert_called_once()

    def test_mismatch_warning_logged_on_startup(self, tmp_path, caplog):
        db_url = f"sqlite:///{tmp_path}/warn_startup.db"
        settings = Settings(database_url=db_url, auto_upgrade=False)
        app = create_app(settings)
        with (
            patch("h4ckath0n.app.get_schema_status") as mock_status,
            patch("h4ckath0n.app.Base.metadata.create_all"),
            caplog.at_level(logging.WARNING),
        ):
            mock_status.return_value.warning = "database schema revision is behind code migrations"
            from fastapi.testclient import TestClient

            with TestClient(app):
                pass
        assert "database schema revision is behind code migrations" in caplog.text


class TestAsyncMigrationHelper:
    def test_normalize_db_url_for_sync_preserves_password_and_strips_asyncpg_query_keys():
        url = (
            "postgresql+asyncpg://flow:flow@localhost:5432/flow_test"
            "?prepared_statement_cache_size=0&sslmode=disable"
        )
        sync = normalize_db_url_for_sync(url)

        assert sync.startswith("postgresql+psycopg://")
        assert "flow:flow@" in sync  # password must not become "***"
        assert "***" not in sync
        assert "prepared_statement_cache_size" not in sync
        assert "sslmode=disable" in sync

    def test_run_upgrade_to_head_async_offloads_to_thread_with_normalized_url(self):
        expected = SchemaStatus(
            state="at_head",
            current_revisions=("0001",),
            head_revisions=("0001",),
            warning=None,
        )
        with patch(
            "h4ckath0n.db.migrations.runtime.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = asyncio.run(run_upgrade_to_head_async("sqlite+aiosqlite:///tmp/test.db"))

        mock_to_thread.assert_awaited_once_with(run_upgrade_to_head_sync, "sqlite:///tmp/test.db")
        assert result == expected
