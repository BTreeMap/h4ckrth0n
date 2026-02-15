"""Comprehensive integration tests for h4ckath0n auth, RBAC, and core features."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)
from fastapi.testclient import TestClient
from jwt.algorithms import ECAlgorithm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from h4ckath0n.app import create_app
from h4ckath0n.auth.models import PasswordResetToken, User
from h4ckath0n.auth.passwords import hash_password, verify_password
from h4ckath0n.auth.service import _hash_token
from h4ckath0n.config import Settings


def _make_device_token(
    user_id: str,
    device_id: str,
    private_key_pem: bytes,
    expire_minutes: int = 15,
    aud: str = "h4ckath0n:http",
) -> str:
    """Create a device-signed ES256 JWT for testing."""
    import jwt as pyjwt

    now = datetime.now(UTC)
    payload: dict = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
    }
    if aud:
        payload["aud"] = aud
    return pyjwt.encode(
        payload,
        private_key_pem,
        algorithm="ES256",
        headers={"kid": device_id},
    )


def _create_device_keypair() -> tuple[bytes, dict]:
    """Generate an EC P-256 keypair. Returns (private_key_pem, public_key_jwk_dict)."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    public_key = private_key.public_key()
    # Export as JWK via PyJWT helper
    jwk_dict = json.loads(ECAlgorithm(ECAlgorithm.SHA256).to_jwk(public_key))
    return private_pem, jwk_dict


@pytest.fixture()
def settings(tmp_path):
    db_path = tmp_path / "test.db"
    return Settings(
        database_url=f"sqlite:///{db_path}",
        env="development",
        first_user_is_admin=False,
        password_auth_enabled=True,
    )


@pytest.fixture()
async def app(settings):
    application = create_app(settings)
    async with application.state.async_engine.begin() as conn:
        from h4ckath0n.db.base import Base

        await conn.run_sync(Base.metadata.create_all)
    yield application
    await application.state.async_engine.dispose()


@pytest.fixture()
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
async def db_session(app):
    async with app.state.async_session_factory() as session:
        yield session


def _register_user_with_device(
    client: TestClient, db_session, email: str, password: str
) -> tuple[str, str, bytes]:
    """Register a user via password route and bind a device key.

    Returns (user_id, device_id, private_key_pem).
    """
    private_pem, public_jwk = _create_device_keypair()
    r = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "device_public_key_jwk": public_jwk,
            "device_label": "test",
        },
    )
    assert r.status_code == 201
    body = r.json()
    return body["user_id"], body["device_id"], private_pem


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_and_verify(self):
        h = hash_password("hunter2")
        assert verify_password("hunter2", h)
        assert not verify_password("wrong", h)


# ---------------------------------------------------------------------------
# Signup / Login happy path (password, device-binding)
# ---------------------------------------------------------------------------


class TestSignupLogin:
    def test_register_returns_device_binding(self, client: TestClient):
        private_pem, public_jwk = _create_device_keypair()
        r = client.post(
            "/auth/register",
            json={
                "email": "alice@example.com",
                "password": "strongP@ss1",
                "device_public_key_jwk": public_jwk,
                "device_label": "test",
            },
        )
        assert r.status_code == 201
        body = r.json()
        assert "user_id" in body
        assert "device_id" in body
        assert body["role"] == "user"
        # No access/refresh tokens
        assert "access_token" not in body
        assert "refresh_token" not in body

    def test_duplicate_register(self, client: TestClient):
        private_pem, public_jwk = _create_device_keypair()
        client.post(
            "/auth/register",
            json={
                "email": "bob@example.com",
                "password": "strongP@ss1",
                "device_public_key_jwk": public_jwk,
            },
        )
        r = client.post(
            "/auth/register",
            json={
                "email": "bob@example.com",
                "password": "strongP@ss1",
                "device_public_key_jwk": public_jwk,
            },
        )
        assert r.status_code == 409

    def test_login_success(self, client: TestClient):
        private_pem, public_jwk = _create_device_keypair()
        client.post(
            "/auth/register",
            json={
                "email": "carol@example.com",
                "password": "strongP@ss1",
                "device_public_key_jwk": public_jwk,
            },
        )
        private_pem2, public_jwk2 = _create_device_keypair()
        r = client.post(
            "/auth/login",
            json={
                "email": "carol@example.com",
                "password": "strongP@ss1",
                "device_public_key_jwk": public_jwk2,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert "user_id" in body
        assert "device_id" in body
        assert "access_token" not in body
        assert "refresh_token" not in body

    def test_login_bad_password(self, client: TestClient):
        private_pem, public_jwk = _create_device_keypair()
        client.post(
            "/auth/register",
            json={
                "email": "dave@example.com",
                "password": "strongP@ss1",
                "device_public_key_jwk": public_jwk,
            },
        )
        r = client.post(
            "/auth/login",
            json={"email": "dave@example.com", "password": "wrong"},
        )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Device-signed JWT protects endpoint
# ---------------------------------------------------------------------------


class TestProtectedEndpoint:
    def test_no_token_rejected(self, client: TestClient, app):
        from h4ckath0n.auth import require_user

        @app.get("/protected")
        def protected(user=require_user()):
            return {"id": user.id}

        r = client.get("/protected")
        assert r.status_code in (401, 403)

    def test_valid_device_token_accepted(self, client: TestClient, app, db_session):
        from h4ckath0n.auth import require_user

        @app.get("/protected2")
        def protected2(user=require_user()):
            return {"id": user.id, "email": user.email}

        user_id, device_id, private_pem = _register_user_with_device(
            client, db_session, "eve@example.com", "strongP@ss1"
        )
        token = _make_device_token(user_id, device_id, private_pem)
        r = client.get("/protected2", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["email"] == "eve@example.com"


# ---------------------------------------------------------------------------
# Admin role gate
# ---------------------------------------------------------------------------


class TestAdminGate:
    async def test_non_admin_rejected(self, client: TestClient, app, db_session):
        from h4ckath0n.auth import require_admin

        @app.get("/admin-only")
        def admin_only(user=require_admin()):
            return {"ok": True}

        user_id, device_id, private_pem = _register_user_with_device(
            client, db_session, "frank@example.com", "strongP@ss1"
        )
        token = _make_device_token(user_id, device_id, private_pem)
        r = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    async def test_admin_accepted(self, client: TestClient, app, db_session: AsyncSession):
        from h4ckath0n.auth import require_admin

        @app.get("/admin-only2")
        def admin_only2(user=require_admin()):
            return {"ok": True}

        user_id, device_id, private_pem = _register_user_with_device(
            client, db_session, "grace@example.com", "strongP@ss1"
        )
        # Promote to admin directly in DB
        result = await db_session.execute(select(User).filter(User.email == "grace@example.com"))
        user = result.scalars().first()
        user.role = "admin"
        await db_session.commit()

        token = _make_device_token(user_id, device_id, private_pem)
        r = client.get("/admin-only2", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Scope gate (from DB, not JWT)
# ---------------------------------------------------------------------------


class TestScopeGate:
    def test_missing_scope_rejected(self, client: TestClient, app, db_session):
        from h4ckath0n.auth import require_scopes

        @app.post("/billing/refund")
        def refund(user=require_scopes("billing:refund")):
            return {"status": "ok"}

        user_id, device_id, private_pem = _register_user_with_device(
            client, db_session, "heidi@example.com", "strongP@ss1"
        )
        token = _make_device_token(user_id, device_id, private_pem)
        r = client.post("/billing/refund", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    async def test_present_scope_accepted(self, client: TestClient, app, db_session: AsyncSession):
        from h4ckath0n.auth import require_scopes

        @app.post("/billing/refund2")
        def refund2(user=require_scopes("billing:refund")):
            return {"status": "ok"}

        user_id, device_id, private_pem = _register_user_with_device(
            client, db_session, "ivan@example.com", "strongP@ss1"
        )
        result = await db_session.execute(select(User).filter(User.email == "ivan@example.com"))
        user = result.scalars().first()
        user.scopes = "billing:refund"
        await db_session.commit()

        token = _make_device_token(user_id, device_id, private_pem)
        r = client.post("/billing/refund2", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# No refresh/logout routes
# ---------------------------------------------------------------------------


class TestNoRefreshRoutes:
    def test_refresh_route_removed(self, client: TestClient):
        r = client.post("/auth/refresh", json={"refresh_token": "x"})
        assert r.status_code in (404, 405)

    def test_logout_route_removed(self, client: TestClient):
        r = client.post("/auth/logout", json={"refresh_token": "x"})
        assert r.status_code in (404, 405)


# ---------------------------------------------------------------------------
# Password reset – time-limited & single-use (now binds device)
# ---------------------------------------------------------------------------


class TestPasswordReset:
    def test_request_always_200(self, client: TestClient):
        # Even for unknown email – prevents enumeration.
        r = client.post(
            "/auth/password-reset/request",
            json={"email": "nobody@example.com"},
        )
        assert r.status_code == 200

    async def test_full_reset_flow(self, client: TestClient, db_session: AsyncSession):
        _private_pem, public_jwk = _create_device_keypair()
        client.post(
            "/auth/register",
            json={
                "email": "luna@example.com",
                "password": "oldP@ss1",
                "device_public_key_jwk": public_jwk,
            },
        )
        # Request reset
        client.post(
            "/auth/password-reset/request",
            json={"email": "luna@example.com"},
        )
        from h4ckath0n.auth.service import create_password_reset_token

        raw = await create_password_reset_token(db_session, "luna@example.com")
        assert raw is not None

        new_pem, new_jwk = _create_device_keypair()
        # Confirm reset – also binds a new device
        r = client.post(
            "/auth/password-reset/confirm",
            json={
                "token": raw,
                "new_password": "newP@ss1",
                "device_public_key_jwk": new_jwk,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert "user_id" in body
        assert "device_id" in body

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

    async def test_single_use(self, client: TestClient, db_session: AsyncSession):
        _p, jwk = _create_device_keypair()
        client.post(
            "/auth/register",
            json={
                "email": "mike@example.com",
                "password": "oldP@ss1",
                "device_public_key_jwk": jwk,
            },
        )
        from h4ckath0n.auth.service import create_password_reset_token

        raw = await create_password_reset_token(db_session, "mike@example.com")
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

    async def test_expired_token_rejected(self, client: TestClient, db_session: AsyncSession):
        _p, jwk = _create_device_keypair()
        client.post(
            "/auth/register",
            json={
                "email": "nancy@example.com",
                "password": "oldP@ss1",
                "device_public_key_jwk": jwk,
            },
        )
        from h4ckath0n.auth.service import create_password_reset_token

        raw = await create_password_reset_token(db_session, "nancy@example.com", expire_minutes=30)
        assert raw is not None
        # Manually expire the token
        result = await db_session.execute(
            select(PasswordResetToken).filter(PasswordResetToken.token_hash == _hash_token(raw))
        )
        prt = result.scalars().first()
        prt.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await db_session.commit()

        r = client.post(
            "/auth/password-reset/confirm",
            json={"token": raw, "new_password": "newP@ss1"},
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Bootstrap admin
# ---------------------------------------------------------------------------


class TestBootstrapAdmin:
    async def test_first_user_admin(self, tmp_path):
        db_path = tmp_path / "admin_test.db"
        s = Settings(
            database_url=f"sqlite:///{db_path}",
            first_user_is_admin=True,
            password_auth_enabled=True,
        )
        app = create_app(s)
        with TestClient(app) as c:
            _p, jwk = _create_device_keypair()
            reg = c.post(
                "/auth/register",
                json={
                    "email": "first@example.com",
                    "password": "P@ss1",
                    "device_public_key_jwk": jwk,
                },
            )
            assert reg.status_code == 201
            # Verify role in DB
            async with app.state.async_session_factory() as session:
                result = await session.execute(
                    select(User).filter(User.email == "first@example.com")
                )
                user = result.scalars().first()
                assert user.role == "admin"

    async def test_bootstrap_admin_emails(self, tmp_path):
        db_path = tmp_path / "admin_test2.db"
        s = Settings(
            database_url=f"sqlite:///{db_path}",
            bootstrap_admin_emails=["boss@example.com"],
            password_auth_enabled=True,
        )
        app = create_app(s)
        with TestClient(app) as c:
            _p1, jwk1 = _create_device_keypair()
            c.post(
                "/auth/register",
                json={
                    "email": "regular@example.com",
                    "password": "P@ss1",
                    "device_public_key_jwk": jwk1,
                },
            )
            _p2, jwk2 = _create_device_keypair()
            c.post(
                "/auth/register",
                json={
                    "email": "boss@example.com",
                    "password": "P@ss1",
                    "device_public_key_jwk": jwk2,
                },
            )
            async with app.state.async_session_factory() as session:
                result = await session.execute(
                    select(User).filter(User.email == "regular@example.com")
                )
                regular = result.scalars().first()
                result = await session.execute(
                    select(User).filter(User.email == "boss@example.com")
                )
                boss = result.scalars().first()
                assert regular.role == "user"
                assert boss.role == "admin"


# ---------------------------------------------------------------------------
# Observability – trace id header & redaction
# ---------------------------------------------------------------------------


class TestObservability:
    def test_trace_id_header(self, tmp_path):
        from h4ckath0n.obs import ObservabilitySettings, init_observability

        db_path = tmp_path / "obs_test.db"
        s = Settings(
            database_url=f"sqlite:///{db_path}",
        )
        app = create_app(s)
        init_observability(app, ObservabilitySettings())
        with TestClient(app) as c:
            r = c.get("/health")
            assert "x-trace-id" in r.headers

    def test_redact_headers(self):
        from h4ckath0n.obs.redaction import redact_headers

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
        from h4ckath0n.obs.redaction import redact_value

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
            os.environ.pop("H4CKATH0N_OPENAI_API_KEY", None)
            with pytest.raises(RuntimeError, match="No OpenAI API key"):
                from h4ckath0n.llm import llm

                llm()


# ---------------------------------------------------------------------------
# Device-signed JWT verification
# ---------------------------------------------------------------------------


class TestDeviceJWTVerification:
    def test_expired_device_token_rejected(self, client: TestClient, app, db_session):
        from h4ckath0n.auth import require_user

        @app.get("/verify-exp")
        def verify_exp(user=require_user()):
            return {"id": user.id}

        user_id, device_id, private_pem = _register_user_with_device(
            client, db_session, "exp-test@example.com", "P@ss1"
        )
        token = _make_device_token(user_id, device_id, private_pem, expire_minutes=-1)
        r = client.get("/verify-exp", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_unknown_device_rejected(self, client: TestClient, app, db_session):
        from h4ckath0n.auth import require_user

        @app.get("/verify-kid")
        def verify_kid(user=require_user()):
            return {"id": user.id}

        private_pem, _public_jwk = _create_device_keypair()
        token = _make_device_token("u" + "a" * 31, "d" + "a" * 31, private_pem)
        r = client.get("/verify-kid", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401
