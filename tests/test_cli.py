"""Tests for the operator CLI and packaged Alembic migrations."""

from __future__ import annotations

import argparse
import importlib.resources
import json
import os
import subprocess
import sys

from sqlalchemy.engine import make_url

import h4ckath0n.cli as cli_module
from h4ckath0n.cli import (
    EXIT_BAD_ARGS,
    EXIT_LAST_PASSKEY,
    EXIT_PROD_INIT,
    EXIT_STAMP_REQUIRED,
    _normalize_db_url_for_sync,
    _normalize_scopes,
)

# ---------------------------------------------------------------------------
# Packaged migrations tests
# ---------------------------------------------------------------------------


class TestPackagedMigrations:
    def test_migrations_package_importable(self):
        migrations = importlib.resources.files("h4ckath0n.db.migrations")
        assert migrations is not None

    def test_env_py_exists(self):
        migrations = importlib.resources.files("h4ckath0n.db.migrations")
        env_py = migrations / "env.py"
        assert hasattr(env_py, "is_file") and env_py.is_file()

    def test_versions_dir_exists(self):
        migrations = importlib.resources.files("h4ckath0n.db.migrations")
        versions = migrations / "versions"
        assert hasattr(versions, "is_dir") and versions.is_dir()

    def test_versions_contain_migration_files(self):
        migrations = importlib.resources.files("h4ckath0n.db.migrations")
        versions = migrations / "versions"
        # Check that at least one migration .py file exists (excluding __init__.py)
        migration_files = [
            f.name
            for f in versions.iterdir()
            if hasattr(f, "name") and f.name.endswith(".py") and f.name != "__init__.py"
        ]
        assert len(migration_files) >= 1
        assert any("0001" in f for f in migration_files)

    def test_script_template_exists(self):
        migrations = importlib.resources.files("h4ckath0n.db.migrations")
        script_template = migrations / "script.py.mako"
        assert hasattr(script_template, "is_file") and script_template.is_file()


# ---------------------------------------------------------------------------
# URL normalization
# ---------------------------------------------------------------------------


class TestNormalizeDbUrl:
    def test_sqlite_aiosqlite(self):
        assert (
            make_url(_normalize_db_url_for_sync("sqlite+aiosqlite:///test.db")).drivername
            == "sqlite"
        )

    def test_postgresql_asyncpg(self):
        normalized = make_url(_normalize_db_url_for_sync("postgresql+asyncpg://u:p@host/db"))
        assert normalized.drivername == "postgresql+psycopg"
        assert normalized.username == "u"
        assert normalized.host == "host"
        assert normalized.database == "db"

    def test_postgresql_asyncpg_drops_asyncpg_only_query_keys(self):
        normalized = make_url(
            _normalize_db_url_for_sync(
                "postgresql+asyncpg://u:p@host:5432/db"
                "?sslmode=require"
                "&prepared_statement_cache_size=0"
                "&prepared_statement_name_func=x"
                "&application_name=h4"
            )
        )
        assert normalized.drivername == "postgresql+psycopg"
        assert normalized.query == {
            "sslmode": "require",
            "application_name": "h4",
        }

    def test_postgresql_plain(self):
        normalized = make_url(_normalize_db_url_for_sync("postgresql://u:p@host/db"))
        assert normalized.drivername == "postgresql+psycopg"
        assert normalized.username == "u"
        assert normalized.host == "host"
        assert normalized.database == "db"

    def test_postgres_shorthand(self):
        normalized = make_url(_normalize_db_url_for_sync("postgres://u:p@host/db"))
        assert normalized.drivername == "postgresql+psycopg"
        assert normalized.username == "u"
        assert normalized.host == "host"
        assert normalized.database == "db"

    def test_sqlite_unchanged(self):
        assert make_url(_normalize_db_url_for_sync("sqlite:///test.db")).drivername == "sqlite"


class TestAlembicUrlNormalization:
    def test_db_migrate_current_passes_sync_url_into_alembic_config(self, monkeypatch):
        captured: dict[str, str] = {}

        def _fake_current(cfg):  # type: ignore[no-untyped-def]
            captured["sqlalchemy.url"] = cfg.get_main_option("sqlalchemy.url")

        monkeypatch.setattr(cli_module.alembic_command, "current", _fake_current)

        args = argparse.Namespace(
            db="sqlite+aiosqlite:///./test.db",
            format="json",
            pretty=False,
        )
        exit_code = cli_module._cmd_db_migrate_current(args)
        assert exit_code == 0
        assert make_url(captured["sqlalchemy.url"]) == make_url("sqlite:///./test.db")


# ---------------------------------------------------------------------------
# Scopes normalization
# ---------------------------------------------------------------------------


class TestNormalizeScopes:
    def test_basic(self):
        assert _normalize_scopes("a,b,c") == "a,b,c"

    def test_dedup(self):
        assert _normalize_scopes("a,b,a") == "a,b"

    def test_trim(self):
        assert _normalize_scopes(" a , b , c ") == "a,b,c"

    def test_empty_segments(self):
        assert _normalize_scopes("a,,b,,") == "a,b"

    def test_empty_string(self):
        assert _normalize_scopes("") == ""


# ---------------------------------------------------------------------------
# CLI integration (using subprocess to avoid sys.exit leaking)
# ---------------------------------------------------------------------------


def _run_cli(
    *args: str, env_override: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    """Run the CLI via ``python -m h4ckath0n``."""
    env = os.environ.copy()
    if env_override:
        env.update(env_override)
    return subprocess.run(
        [sys.executable, "-m", "h4ckath0n", *args],
        capture_output=True,
        text=True,
        env=env,
    )


class TestCLIHelp:
    def test_help_returns_zero(self):
        result = _run_cli("--help")
        assert result.returncode == 0
        assert "h4ckath0n" in result.stdout

    def test_db_help(self):
        result = _run_cli("db", "--help")
        assert result.returncode == 0


class TestCLIDbPing:
    def test_ping_sqlite(self, tmp_path):
        db_url = f"sqlite:///{tmp_path}/ping_test.db"
        result = _run_cli("db", "ping", "--db", db_url)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["ok"] is True
        assert data["schema_state"] == "fresh"


class TestCLIDbInit:
    def test_init_requires_yes(self, tmp_path):
        db_url = f"sqlite:///{tmp_path}/init_test.db"
        result = _run_cli("db", "init", "--db", db_url)
        assert result.returncode == EXIT_BAD_ARGS

    def test_init_success(self, tmp_path):
        db_url = f"sqlite:///{tmp_path}/init_test.db"
        result = _run_cli("db", "init", "--db", db_url, "--yes")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["ok"] is True

    def test_init_blocked_in_production(self, tmp_path):
        db_url = f"sqlite:///{tmp_path}/init_test.db"
        result = _run_cli(
            "db", "init", "--db", db_url, "--yes", env_override={"H4CKATH0N_ENV": "production"}
        )
        assert result.returncode == EXIT_PROD_INIT

    def test_init_production_with_force(self, tmp_path):
        db_url = f"sqlite:///{tmp_path}/init_test.db"
        result = _run_cli(
            "db",
            "init",
            "--db",
            db_url,
            "--yes",
            "--force",
            env_override={"H4CKATH0N_ENV": "production"},
        )
        assert result.returncode == 0


class TestCLIDbMigrate:
    def test_upgrade_requires_yes(self, tmp_path):
        db_url = f"sqlite:///{tmp_path}/mig_test.db"
        result = _run_cli("db", "migrate", "upgrade", "--db", db_url)
        assert result.returncode == EXIT_BAD_ARGS

    def test_upgrade_on_fresh_db(self, tmp_path):
        db_url = f"sqlite:///{tmp_path}/mig_test.db"
        result = _run_cli("db", "migrate", "upgrade", "--to", "head", "--db", db_url, "--yes")
        assert result.returncode == 0, result.stderr

    def test_stamp_requires_yes(self, tmp_path):
        db_url = f"sqlite:///{tmp_path}/stamp_test.db"
        result = _run_cli("db", "migrate", "stamp", "--to", "0001", "--db", db_url)
        assert result.returncode == EXIT_BAD_ARGS

    def test_current(self, tmp_path):
        db_url = f"sqlite:///{tmp_path}/current_test.db"
        result = _run_cli("db", "migrate", "current", "--db", db_url)
        assert result.returncode == 0

    def test_current_with_sqlite_aiosqlite_url(self, tmp_path):
        db_url = f"sqlite+aiosqlite:///{tmp_path}/current_test_async.db"
        result = _run_cli("db", "migrate", "current", "--db", db_url)
        assert result.returncode == 0
        assert "MissingGreenlet" not in result.stderr

    def test_heads(self, tmp_path):
        db_url = f"sqlite:///{tmp_path}/heads_test.db"
        result = _run_cli("db", "migrate", "heads", "--db", db_url)
        assert result.returncode == 0

    def test_upgrade_safety_gate(self, tmp_path):
        """If h4ckath0n tables exist without alembic_version, exit 6."""
        db_url = f"sqlite:///{tmp_path}/gate_test.db"
        # First create tables via db init
        _run_cli("db", "init", "--db", db_url, "--yes")
        # Now try upgrade – should detect existing tables without alembic_version
        result = _run_cli("db", "migrate", "upgrade", "--to", "head", "--db", db_url, "--yes")
        assert result.returncode == EXIT_STAMP_REQUIRED


class TestCLIUsersOperations:
    def _init_db(self, tmp_path):
        db_url = f"sqlite:///{tmp_path}/users_test.db"
        from sqlalchemy import create_engine

        import h4ckath0n.auth.models  # noqa: F401
        from h4ckath0n.db.base import Base

        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        engine.dispose()
        return db_url

    def _create_user(self, db_url, email="test@example.com"):
        """Create a user directly via SQLAlchemy for testing."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        import h4ckath0n.auth.models as models  # noqa: F401

        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        with Session(engine) as session:
            user = models.User(email=email)
            session.add(user)
            session.commit()
            session.refresh(user)
            uid = user.id
        engine.dispose()
        return uid

    def test_users_list(self, tmp_path):
        db_url = self._init_db(tmp_path)
        self._create_user(db_url)
        result = _run_cli("users", "list", "--db", db_url)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) >= 1

    def test_users_show(self, tmp_path):
        db_url = self._init_db(tmp_path)
        uid = self._create_user(db_url)
        result = _run_cli("users", "show", "--user-id", uid, "--db", db_url)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["id"] == uid
        assert "devices_total" in data

    def test_users_set_role(self, tmp_path):
        db_url = self._init_db(tmp_path)
        uid = self._create_user(db_url)
        result = _run_cli(
            "users", "set-role", "--user-id", uid, "--role", "admin", "--db", db_url, "--yes"
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["role"] == "admin"

    def test_users_disable_enable(self, tmp_path):
        db_url = self._init_db(tmp_path)
        uid = self._create_user(db_url)

        result = _run_cli("users", "disable", "--user-id", uid, "--db", db_url, "--yes")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["disabled_at"] is not None

        result = _run_cli("users", "enable", "--user-id", uid, "--db", db_url, "--yes")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["disabled_at"] is None

    def test_users_scopes_add(self, tmp_path):
        db_url = self._init_db(tmp_path)
        uid = self._create_user(db_url)
        result = _run_cli(
            "users",
            "scopes",
            "add",
            "--user-id",
            uid,
            "--scope",
            "billing:read",
            "--scope",
            "billing:write",
            "--db",
            db_url,
            "--yes",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "billing:read" in data["scopes"]
        assert "billing:write" in data["scopes"]

    def test_users_scopes_set(self, tmp_path):
        db_url = self._init_db(tmp_path)
        uid = self._create_user(db_url)
        result = _run_cli(
            "users",
            "scopes",
            "set",
            "--user-id",
            uid,
            "--scopes",
            "a:b,c:d",
            "--db",
            db_url,
            "--yes",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["scopes"] == "a:b,c:d"


class TestCLISubprocessWithAsyncDbUrlEnv:
    def test_db_ping_uses_sync_tooling_driver(self, tmp_path):
        db_url = f"sqlite+aiosqlite:///{tmp_path}/ping_env.db"
        result = _run_cli("db", "ping", env_override={"H4CKATH0N_DATABASE_URL": db_url})
        assert result.returncode == 0
        assert "MissingGreenlet" not in result.stderr
        data = json.loads(result.stdout)
        assert data["ok"] is True

    def test_db_migrate_current_uses_sync_tooling_driver(self, tmp_path):
        db_url = f"sqlite+aiosqlite:///{tmp_path}/current_env.db"
        result = _run_cli(
            "db", "migrate", "current", env_override={"H4CKATH0N_DATABASE_URL": db_url}
        )
        assert result.returncode == 0
        assert "MissingGreenlet" not in result.stderr


class TestCLIPasskeysRevoke:
    def _setup(self, tmp_path, n_creds=2):
        """Create user with passkeys for testing."""
        db_url = f"sqlite:///{tmp_path}/pk_test.db"

        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        import h4ckath0n.auth.models  # noqa: F401
        from h4ckath0n.auth.models import User, WebAuthnCredential
        from h4ckath0n.db.base import Base

        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            user = User(email="pk@test.com")
            session.add(user)
            session.flush()
            creds = []
            for i in range(n_creds):
                cred = WebAuthnCredential(
                    user_id=user.id,
                    credential_id=f"cred-{user.id}-{i}",
                    public_key=b"\x00" * 32,
                    sign_count=0,
                )
                session.add(cred)
                creds.append(cred)
            session.commit()
            for c in creds:
                session.refresh(c)
            session.refresh(user)
            uid = user.id
            key_ids = [c.id for c in creds]
        engine.dispose()
        return db_url, uid, key_ids

    def test_revoke_last_passkey_blocked(self, tmp_path):
        db_url, uid, key_ids = self._setup(tmp_path, n_creds=1)
        result = _run_cli("passkeys", "revoke", "--key-id", key_ids[0], "--db", db_url, "--yes")
        assert result.returncode == EXIT_LAST_PASSKEY
        assert "last active passkey" in result.stderr

    def test_revoke_one_of_two(self, tmp_path):
        db_url, uid, key_ids = self._setup(tmp_path, n_creds=2)
        result = _run_cli("passkeys", "revoke", "--key-id", key_ids[0], "--db", db_url, "--yes")
        assert result.returncode == 0
