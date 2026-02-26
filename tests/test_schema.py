"""Test initial migration schema changes."""

from __future__ import annotations

import json
from tests.conftest import run_cli

class TestSchemaPrefix:
    def test_tables_have_prefix(self, tmp_path):
        db_url = f"sqlite:///{tmp_path}/prefix_test.db"
        # Run migration to create tables
        result = run_cli("db", "migrate", "upgrade", "--to", "head", "--db", db_url, "--yes")
        assert result.returncode == 0

        # Check tables using sqlite3
        import sqlite3
        conn = sqlite3.connect(f"{tmp_path}/prefix_test.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        expected_tables = [
            "h4ckath0n_users",
            "h4ckath0n_webauthn_credentials",
            "h4ckath0n_webauthn_challenges",
            "h4ckath0n_password_reset_tokens",
            "h4ckath0n_devices",
            "h4ckath0n_alembic_version"
        ]

        for table in expected_tables:
            assert table in tables, f"Table {table} not found in {tables}"
