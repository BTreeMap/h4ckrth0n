"""Comprehensive integration tests for h4ckrth0n auth, RBAC, and core features."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from h4ckrth0n.app import create_app
from h4ckrth0n.auth.models import PasswordResetToken, User
from h4ckrth0n.auth.passwords import hash_password, verify_password
from h4ckrth0n.auth.service import _hash_token
from h4ckrth0n.config import Settings


@pytest.fixture()
def settings(tmp_path):
    db_path = tmp_path / "test.db"
    return Settings(
        database_url=f"sqlite:///{db_path}",
        auth_signing_key="test-secret-key-for-unit-tests-minimum-32-bytes",
        env="development",
        first_user_is_admin=False,
        password_auth_enabled=True,
    )


@pytest.fixture()
def app(settings):
    return create_app(settings)


@pytest.fixture()
def client(app):
    return TestClient(app)


@pytest.fixture()
def db_session(app):
    session = app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_and_verify(self):
        h = hash_password("hunter2")
        assert verify_password("hunter2", h)
        assert not verify_password("wrong", h)


# ---------------------------------------------------------------------------
# Signup / Login happy path
# ---------------------------------------------------------------------------


class TestSignupLogin:
    def test_register_returns_tokens(self, client: TestClient):
        r = client.post(
            "/auth/register",
            json={"email": "alice@example.com", "password": "strongP@ss1"},
        )
        assert r.status_code == 201
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    def test_duplicate_register(self, client: TestClient):
        client.post(
            "/auth/register",
            json={"email": "bob@example.com", "password": "strongP@ss1"},
        )
        r = client.post(
            "/auth/register",
            json={"email": "bob@example.com", "password": "strongP@ss1"},
        )
        assert r.status_code == 409

    def test_login_success(self, client: TestClient):
        client.post(
            "/auth/register",
            json={"email": "carol@example.com", "password": "strongP@ss1"},
        )
        r = client.post(
            "/auth/login",
            json={"email": "carol@example.com", "password": "strongP@ss1"},
        )
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_bad_password(self, client: TestClient):
        client.post(
            "/auth/register",
            json={"email": "dave@example.com", "password": "strongP@ss1"},
        )
        r = client.post(
            "/auth/login",
            json={"email": "dave@example.com", "password": "wrong"},
        )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Access token protects endpoint
# ---------------------------------------------------------------------------


class TestProtectedEndpoint:
    def test_no_token_rejected(self, client: TestClient, app):
        from h4ckrth0n.auth import require_user

        @app.get("/protected")
        def protected(user=require_user()):
            return {"id": user.id}

        r = client.get("/protected")
        assert r.status_code == 401

    def test_valid_token_accepted(self, client: TestClient, app, settings):
        from h4ckrth0n.auth import require_user

        @app.get("/protected2")
        def protected2(user=require_user()):
            return {"id": user.id, "email": user.email}

        reg = client.post(
            "/auth/register",
            json={"email": "eve@example.com", "password": "strongP@ss1"},
        )
        token = reg.json()["access_token"]
        r = client.get("/protected2", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["email"] == "eve@example.com"


# ---------------------------------------------------------------------------
# Admin role gate
# ---------------------------------------------------------------------------


class TestAdminGate:
    def test_non_admin_rejected(self, client: TestClient, app):
        from h4ckrth0n.auth import require_admin

        @app.get("/admin-only")
        def admin_only(user=require_admin()):
            return {"ok": True}

        reg = client.post(
            "/auth/register",
            json={"email": "frank@example.com", "password": "strongP@ss1"},
        )
        token = reg.json()["access_token"]
        r = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    def test_admin_accepted(self, client: TestClient, app, settings, db_session):
        from h4ckrth0n.auth import require_admin

        @app.get("/admin-only2")
        def admin_only2(user=require_admin()):
            return {"ok": True}

        client.post(
            "/auth/register",
            json={"email": "grace@example.com", "password": "strongP@ss1"},
        )
        # Promote to admin directly in DB
        user = db_session.query(User).filter(User.email == "grace@example.com").first()
        user.role = "admin"
        db_session.commit()

        # Re-login to get new token with admin role
        login = client.post(
            "/auth/login",
            json={"email": "grace@example.com", "password": "strongP@ss1"},
        )
        token = login.json()["access_token"]
        r = client.get("/admin-only2", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Scope gate
# ---------------------------------------------------------------------------


class TestScopeGate:
    def test_missing_scope_rejected(self, client: TestClient, app):
        from h4ckrth0n.auth import require_scopes

        @app.post("/billing/refund")
        def refund(claims=require_scopes("billing:refund")):
            return {"status": "ok"}

        reg = client.post(
            "/auth/register",
            json={"email": "heidi@example.com", "password": "strongP@ss1"},
        )
        token = reg.json()["access_token"]
        r = client.post("/billing/refund", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    def test_present_scope_accepted(self, client: TestClient, app, settings, db_session):
        from h4ckrth0n.auth import require_scopes

        @app.post("/billing/refund2")
        def refund2(claims=require_scopes("billing:refund")):
            return {"status": "ok"}

        client.post(
            "/auth/register",
            json={"email": "ivan@example.com", "password": "strongP@ss1"},
        )
        user = db_session.query(User).filter(User.email == "ivan@example.com").first()
        user.scopes = "billing:refund"
        db_session.commit()

        login = client.post(
            "/auth/login",
            json={"email": "ivan@example.com", "password": "strongP@ss1"},
        )
        token = login.json()["access_token"]
        r = client.post("/billing/refund2", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Refresh token rotation
# ---------------------------------------------------------------------------


class TestRefreshRotation:
    def test_refresh_rotates(self, client: TestClient):
        reg = client.post(
            "/auth/register",
            json={"email": "judy@example.com", "password": "strongP@ss1"},
        )
        rt1 = reg.json()["refresh_token"]

        r = client.post("/auth/refresh", json={"refresh_token": rt1})
        assert r.status_code == 200
        body = r.json()
        rt2 = body["refresh_token"]
        assert rt2 != rt1  # rotated

        # Old token should be revoked.
        r2 = client.post("/auth/refresh", json={"refresh_token": rt1})
        assert r2.status_code == 401

    def test_logout_revokes(self, client: TestClient):
        reg = client.post(
            "/auth/register",
            json={"email": "karl@example.com", "password": "strongP@ss1"},
        )
        rt = reg.json()["refresh_token"]
        client.post("/auth/logout", json={"refresh_token": rt})

        r = client.post("/auth/refresh", json={"refresh_token": rt})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Password reset – time-limited & single-use
# ---------------------------------------------------------------------------


class TestPasswordReset:
    def test_request_always_200(self, client: TestClient):
        # Even for unknown email – prevents enumeration.
        r = client.post(
            "/auth/password-reset/request",
            json={"email": "nobody@example.com"},
        )
        assert r.status_code == 200

    def test_full_reset_flow(self, client: TestClient, db_session):
        client.post(
            "/auth/register",
            json={"email": "luna@example.com", "password": "oldP@ss1"},
        )
        # Request reset
        client.post(
            "/auth/password-reset/request",
            json={"email": "luna@example.com"},
        )
        # Get the raw token from DB (in real life it would be emailed).
        prt = (
            db_session.query(PasswordResetToken)
            .join(User, PasswordResetToken.user_id == User.id)
            .filter(User.email == "luna@example.com")
            .first()
        )
        assert prt is not None
        # We need the raw token. Since we stored a hash, we must re-create one
        # for testing. Let's directly create one via the service.
        from h4ckrth0n.auth.service import create_password_reset_token

        raw = create_password_reset_token(db_session, "luna@example.com")
        assert raw is not None

        # Confirm reset
        r = client.post(
            "/auth/password-reset/confirm",
            json={"token": raw, "new_password": "newP@ss1"},
        )
        assert r.status_code == 200

        # Old password should no longer work
        r2 = client.post(
            "/auth/login",
            json={"email": "luna@example.com", "password": "oldP@ss1"},
        )
        assert r2.status_code == 401

        # New password should work
        r3 = client.post(
            "/auth/login",
            json={"email": "luna@example.com", "password": "newP@ss1"},
        )
        assert r3.status_code == 200

    def test_single_use(self, client: TestClient, db_session):
        client.post(
            "/auth/register",
            json={"email": "mike@example.com", "password": "oldP@ss1"},
        )
        from h4ckrth0n.auth.service import create_password_reset_token

        raw = create_password_reset_token(db_session, "mike@example.com")
        assert raw is not None

        # Use once
        r = client.post(
            "/auth/password-reset/confirm",
            json={"token": raw, "new_password": "newP@ss1"},
        )
        assert r.status_code == 200

        # Second use should fail
        r2 = client.post(
            "/auth/password-reset/confirm",
            json={"token": raw, "new_password": "anotherP@ss"},
        )
        assert r2.status_code == 400

    def test_expired_token_rejected(self, client: TestClient, db_session):
        client.post(
            "/auth/register",
            json={"email": "nancy@example.com", "password": "oldP@ss1"},
        )
        from h4ckrth0n.auth.service import create_password_reset_token

        raw = create_password_reset_token(db_session, "nancy@example.com", expire_minutes=30)
        assert raw is not None
        # Manually expire the token
        prt = (
            db_session.query(PasswordResetToken)
            .filter(PasswordResetToken.token_hash == _hash_token(raw))
            .first()
        )
        prt.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db_session.commit()

        r = client.post(
            "/auth/password-reset/confirm",
            json={"token": raw, "new_password": "newP@ss1"},
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Bootstrap admin
# ---------------------------------------------------------------------------


class TestBootstrapAdmin:
    def test_first_user_admin(self, tmp_path):
        db_path = tmp_path / "admin_test.db"
        s = Settings(
            database_url=f"sqlite:///{db_path}",
            auth_signing_key="test-key-minimum-32-bytes-for-safety",
            first_user_is_admin=True,
            password_auth_enabled=True,
        )
        app = create_app(s)
        c = TestClient(app)
        reg = c.post(
            "/auth/register",
            json={"email": "first@example.com", "password": "P@ss1"},
        )
        assert reg.status_code == 201
        # Verify role in DB
        session = app.state.session_factory()
        user = session.query(User).filter(User.email == "first@example.com").first()
        assert user.role == "admin"
        session.close()

    def test_bootstrap_admin_emails(self, tmp_path):
        db_path = tmp_path / "admin_test2.db"
        s = Settings(
            database_url=f"sqlite:///{db_path}",
            auth_signing_key="test-key-minimum-32-bytes-for-safety",
            bootstrap_admin_emails=["boss@example.com"],
            password_auth_enabled=True,
        )
        app = create_app(s)
        c = TestClient(app)
        c.post(
            "/auth/register",
            json={"email": "regular@example.com", "password": "P@ss1"},
        )
        c.post(
            "/auth/register",
            json={"email": "boss@example.com", "password": "P@ss1"},
        )
        session = app.state.session_factory()
        regular = session.query(User).filter(User.email == "regular@example.com").first()
        boss = session.query(User).filter(User.email == "boss@example.com").first()
        assert regular.role == "user"
        assert boss.role == "admin"
        session.close()


# ---------------------------------------------------------------------------
# Observability – trace id header & redaction
# ---------------------------------------------------------------------------


class TestObservability:
    def test_trace_id_header(self, tmp_path):
        from h4ckrth0n.obs import ObservabilitySettings, init_observability

        db_path = tmp_path / "obs_test.db"
        s = Settings(
            database_url=f"sqlite:///{db_path}",
            auth_signing_key="test-key-minimum-32-bytes-for-safety",
        )
        app = create_app(s)
        init_observability(app, ObservabilitySettings())
        c = TestClient(app)
        r = c.get("/health")
        assert "x-trace-id" in r.headers

    def test_redact_headers(self):
        from h4ckrth0n.obs.redaction import redact_headers

        h = {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.test.sig",
            "Content-Type": "application/json",
            "X-Api-Key": "sk-abcdef123456",
        }
        cleaned = redact_headers(h)
        assert cleaned["Authorization"] == "[REDACTED]"
        assert cleaned["X-Api-Key"] == "[REDACTED]"
        assert cleaned["Content-Type"] == "application/json"

    def test_redact_value(self):
        from h4ckrth0n.obs.redaction import redact_value

        val = "token eyJhbGciOiJIUzI1NiJ9.payload.sig and key sk-abcdefghijklmnopqrstuvwxyz"
        cleaned = redact_value(val)
        assert "eyJ" not in cleaned
        assert "sk-" not in cleaned
        assert "[REDACTED]" in cleaned


# ---------------------------------------------------------------------------
# LLM module – graceful error when not configured
# ---------------------------------------------------------------------------


class TestLLMClient:
    def test_no_api_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            # Ensure keys are cleared
            import os

            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("H4CKRTH0N_OPENAI_API_KEY", None)
            with pytest.raises(RuntimeError, match="No OpenAI API key"):
                from h4ckrth0n.llm import llm

                llm()


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestConfig:
    def test_production_requires_signing_key(self):
        s = Settings(env="production", auth_signing_key="")
        with pytest.raises(RuntimeError, match="H4CKRTH0N_AUTH_SIGNING_KEY"):
            s.effective_signing_key()

    def test_dev_generates_ephemeral_key(self):
        s = Settings(env="development", auth_signing_key="")
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            key = s.effective_signing_key()
        assert len(key) > 10
