"""Tests for passkey (WebAuthn) authentication.

Covers:
- ID generator tests (length, prefix, charset)
- Flow state tests (expiry, consumed flows)
- Last-passkey invariant (revoking only credential blocked, multiple ok, concurrency)
- Route wiring and DB persistence
- WebAuthn config (production requires rp_id/origin)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

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
from h4ckath0n.auth.models import User, WebAuthnChallenge, WebAuthnCredential
from h4ckath0n.auth.passkeys.ids import (
    is_key_id,
    is_user_id,
    new_key_id,
    new_user_id,
)
from h4ckath0n.auth.passkeys.service import (
    LastPasskeyError,
    cleanup_expired_challenges,
    list_passkeys,
    revoke_passkey,
    start_authentication,
    start_registration,
)
from h4ckath0n.auth.service import register_device
from h4ckath0n.config import Settings

_ALLOWED_BASE32 = set("abcdefghijklmnopqrstuvwxyz234567")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def settings(tmp_path):
    db_path = tmp_path / "passkey_test.db"
    return Settings(
        database_url=f"sqlite:///{db_path}",
        env="development",
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


# ---------------------------------------------------------------------------
# ID generator tests
# ---------------------------------------------------------------------------


class TestIdGenerators:
    def test_user_id_length(self):
        uid = new_user_id()
        assert len(uid) == 32

    def test_user_id_prefix(self):
        uid = new_user_id()
        assert uid[0] == "u"

    def test_user_id_charset(self):
        uid = new_user_id()
        assert all(c in _ALLOWED_BASE32 | {"u"} for c in uid)
        # chars after first must be base32
        assert all(c in _ALLOWED_BASE32 for c in uid[1:])

    def test_key_id_length(self):
        kid = new_key_id()
        assert len(kid) == 32

    def test_key_id_prefix(self):
        kid = new_key_id()
        assert kid[0] == "k"

    def test_key_id_charset(self):
        kid = new_key_id()
        assert all(c in _ALLOWED_BASE32 for c in kid[1:])

    def test_is_user_id(self):
        uid = new_user_id()
        assert is_user_id(uid)
        assert not is_user_id("x" + uid[1:])
        assert not is_user_id(uid[:31])  # too short
        assert not is_user_id(uid + "a")  # too long

    def test_is_key_id(self):
        kid = new_key_id()
        assert is_key_id(kid)
        assert not is_key_id("x" + kid[1:])
        assert not is_key_id(kid[:31])

    def test_user_id_not_key_id(self):
        uid = new_user_id()
        assert not is_key_id(uid)

    def test_key_id_not_user_id(self):
        kid = new_key_id()
        assert not is_user_id(kid)

    def test_uniqueness(self):
        ids = {new_user_id() for _ in range(100)}
        assert len(ids) == 100  # all unique


# ---------------------------------------------------------------------------
# Flow state tests (challenge lifecycle)
# ---------------------------------------------------------------------------


class TestFlowState:
    async def test_register_start_creates_flow(self, db_session: AsyncSession, settings):
        flow_id, options = await start_registration(db_session, settings)
        assert flow_id
        assert "challenge" in options
        result = await db_session.execute(select(WebAuthnChallenge).filter_by(id=flow_id))
        flow = result.scalars().first()
        assert flow is not None
        assert flow.kind == "register"
        assert flow.consumed_at is None

    async def test_register_start_creates_user(self, db_session: AsyncSession, settings):
        flow_id, _ = await start_registration(db_session, settings)
        result = await db_session.execute(select(WebAuthnChallenge).filter_by(id=flow_id))
        flow = result.scalars().first()
        result = await db_session.execute(select(User).filter_by(id=flow.user_id))
        user = result.scalars().first()
        assert user is not None
        assert is_user_id(user.id)

    async def test_authentication_start_creates_flow(self, db_session: AsyncSession, settings):
        flow_id, options = await start_authentication(db_session, settings)
        assert flow_id
        assert "challenge" in options
        result = await db_session.execute(select(WebAuthnChallenge).filter_by(id=flow_id))
        flow = result.scalars().first()
        assert flow is not None
        assert flow.kind == "authenticate"
        assert flow.user_id is None  # username-less

    async def test_expired_flow_rejected(self, db_session: AsyncSession, settings):
        from h4ckath0n.auth.passkeys.service import _get_valid_flow

        flow_id, _ = await start_registration(db_session, settings)
        # Manually expire the flow
        result = await db_session.execute(select(WebAuthnChallenge).filter_by(id=flow_id))
        flow = result.scalars().first()
        flow.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await db_session.commit()

        with pytest.raises(ValueError, match="expired"):
            await _get_valid_flow(db_session, flow_id, "register")

    async def test_consumed_flow_rejected(self, db_session: AsyncSession, settings):
        from h4ckath0n.auth.passkeys.service import _consume_flow, _get_valid_flow

        flow_id, _ = await start_registration(db_session, settings)
        result = await db_session.execute(select(WebAuthnChallenge).filter_by(id=flow_id))
        flow = result.scalars().first()
        await _consume_flow(db_session, flow)
        await db_session.commit()

        with pytest.raises(ValueError, match="consumed"):
            await _get_valid_flow(db_session, flow_id, "register")

    async def test_flow_kind_mismatch_rejected(self, db_session: AsyncSession, settings):
        from h4ckath0n.auth.passkeys.service import _get_valid_flow

        flow_id, _ = await start_registration(db_session, settings)
        with pytest.raises(ValueError, match="mismatch"):
            await _get_valid_flow(db_session, flow_id, "authenticate")

    async def test_cleanup_expired_challenges(self, db_session: AsyncSession, settings):
        flow_id, _ = await start_registration(db_session, settings)
        # Expire it
        result = await db_session.execute(select(WebAuthnChallenge).filter_by(id=flow_id))
        flow = result.scalars().first()
        flow.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await db_session.commit()

        deleted = await cleanup_expired_challenges(db_session)
        assert deleted >= 1

        result = await db_session.execute(select(WebAuthnChallenge).filter_by(id=flow_id))
        remaining = result.scalars().first()
        assert remaining is None


# ---------------------------------------------------------------------------
# Last-passkey invariant
# ---------------------------------------------------------------------------


class TestLastPasskeyInvariant:
    async def _create_user_with_passkeys(self, db_session: AsyncSession, count: int = 1):
        """Helper to create a user with *count* active passkeys."""
        user = User()
        db_session.add(user)
        await db_session.flush()

        creds = []
        for i in range(count):
            cred = WebAuthnCredential(
                user_id=user.id,
                credential_id=f"cred-{user.id}-{i}",
                public_key=b"\x00" * 32,
                sign_count=0,
            )
            db_session.add(cred)
            creds.append(cred)
        await db_session.commit()
        for c in creds:
            await db_session.refresh(c)
        await db_session.refresh(user)
        return user, creds

    async def test_revoke_only_credential_blocked(self, db_session: AsyncSession):
        user, creds = await self._create_user_with_passkeys(db_session, count=1)
        with pytest.raises(LastPasskeyError, match="last active passkey"):
            await revoke_passkey(db_session, user, creds[0].id)

    async def test_revoke_one_of_two_allowed(self, db_session: AsyncSession):
        user, creds = await self._create_user_with_passkeys(db_session, count=2)
        await revoke_passkey(db_session, user, creds[0].id)
        # Credential should now be revoked
        await db_session.refresh(creds[0])
        assert creds[0].revoked_at is not None

    async def test_revoke_down_to_one_then_blocked(self, db_session: AsyncSession):
        user, creds = await self._create_user_with_passkeys(db_session, count=2)
        await revoke_passkey(db_session, user, creds[0].id)
        # Now only one active – should block
        with pytest.raises(LastPasskeyError):
            await revoke_passkey(db_session, user, creds[1].id)

    async def test_revoke_already_revoked_raises(self, db_session: AsyncSession):
        user, creds = await self._create_user_with_passkeys(db_session, count=2)
        await revoke_passkey(db_session, user, creds[0].id)
        with pytest.raises(ValueError, match="already revoked"):
            await revoke_passkey(db_session, user, creds[0].id)

    async def test_revoke_nonexistent_raises(self, db_session: AsyncSession):
        user, _ = await self._create_user_with_passkeys(db_session, count=1)
        with pytest.raises(ValueError, match="not found"):
            await revoke_passkey(db_session, user, "knonexistent00000000000000000000")

    async def test_revoke_other_users_credential_fails(self, db_session: AsyncSession):
        user1, creds1 = await self._create_user_with_passkeys(db_session, count=2)
        user2, creds2 = await self._create_user_with_passkeys(db_session, count=2)
        with pytest.raises(ValueError, match="not found"):
            await revoke_passkey(db_session, user1, creds2[0].id)

    async def test_list_passkeys(self, db_session: AsyncSession):
        user, creds = await self._create_user_with_passkeys(db_session, count=3)
        listed = await list_passkeys(db_session, user)
        assert len(listed) == 3
        assert all(is_key_id(c.id) for c in listed)


# ---------------------------------------------------------------------------
# Route wiring tests
# ---------------------------------------------------------------------------


class TestPasskeyRoutes:
    def test_register_start_returns_options(self, client: TestClient):
        r = client.post("/auth/passkey/register/start")
        assert r.status_code == 200
        body = r.json()
        assert "flow_id" in body
        assert "options" in body
        assert "challenge" in body["options"]
        assert "rp" in body["options"]

    def test_login_start_returns_options(self, client: TestClient):
        r = client.post("/auth/passkey/login/start")
        assert r.status_code == 200
        body = r.json()
        assert "flow_id" in body
        assert "options" in body
        assert "challenge" in body["options"]

    def test_register_finish_bad_flow_rejected(self, client: TestClient):
        r = client.post(
            "/auth/passkey/register/finish",
            json={"flow_id": "nonexistent", "credential": {}},
        )
        assert r.status_code == 400

    def test_login_finish_bad_flow_rejected(self, client: TestClient):
        r = client.post(
            "/auth/passkey/login/finish",
            json={"flow_id": "nonexistent", "credential": {}},
        )
        assert r.status_code == 401

    def test_passkeys_list_requires_auth(self, client: TestClient):
        r = client.get("/auth/passkeys")
        assert r.status_code in (401, 403)

    def test_passkey_revoke_requires_auth(self, client: TestClient):
        r = client.post("/auth/passkeys/k00000000000000000000000000000000/revoke")
        assert r.status_code in (401, 403)

    def test_add_start_requires_auth(self, client: TestClient):
        r = client.post("/auth/passkey/add/start")
        assert r.status_code in (401, 403)

    async def test_register_start_creates_user_in_db(
        self, client: TestClient, db_session: AsyncSession
    ):
        r = client.post("/auth/passkey/register/start")
        assert r.status_code == 200
        flow_id = r.json()["flow_id"]
        result = await db_session.execute(select(WebAuthnChallenge).filter_by(id=flow_id))
        flow = result.scalars().first()
        assert flow is not None
        result = await db_session.execute(select(User).filter_by(id=flow.user_id))
        user = result.scalars().first()
        assert user is not None
        assert is_user_id(user.id)


# ---------------------------------------------------------------------------
# Revoke route tests (via HTTP, using DB-seeded credentials)
# ---------------------------------------------------------------------------


class TestPasskeyRevokeRoute:
    async def _setup_user_with_device_token(
        self, client, db_session: AsyncSession, settings, n_creds=2
    ):
        """Create a user with passkeys and a device-signed JWT.

        Returns (user, creds, token).
        """
        import jwt as pyjwt

        user = User()
        db_session.add(user)
        await db_session.flush()

        creds = []
        for i in range(n_creds):
            cred = WebAuthnCredential(
                user_id=user.id,
                credential_id=f"revoke-test-{user.id}-{i}",
                public_key=b"\x00" * 32,
                sign_count=0,
            )
            db_session.add(cred)
            creds.append(cred)
        await db_session.commit()
        for c in creds:
            await db_session.refresh(c)
        await db_session.refresh(user)

        # Create a device keypair and register it
        private_key = ec.generate_private_key(ec.SECP256R1())
        private_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
        public_key = private_key.public_key()
        jwk_dict = json.loads(ECAlgorithm(ECAlgorithm.SHA256).to_jwk(public_key))

        device_id = await register_device(db_session, user.id, jwk_dict, "test")

        now = datetime.now(UTC)
        token = pyjwt.encode(
            {
                "sub": user.id,
                "iat": now,
                "exp": now + timedelta(minutes=15),
                "aud": "h4ckath0n:http",
            },
            private_pem,
            algorithm="ES256",
            headers={"kid": device_id},
        )
        return user, creds, token

    async def test_revoke_one_of_two_via_route(self, client, db_session, settings):
        user, creds, token = await self._setup_user_with_device_token(
            client, db_session, settings, 2
        )
        r = client.post(
            f"/auth/passkeys/{creds[0].id}/revoke",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200

    async def test_revoke_last_passkey_blocked_via_route(self, client, db_session, settings):
        user, creds, token = await self._setup_user_with_device_token(
            client, db_session, settings, 1
        )
        r = client.post(
            f"/auth/passkeys/{creds[0].id}/revoke",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 409
        body = r.json()
        assert body["detail"]["code"] == "LAST_PASSKEY"

    async def test_list_passkeys_via_route(self, client, db_session, settings):
        user, creds, token = await self._setup_user_with_device_token(
            client, db_session, settings, 3
        )
        r = client.get(
            "/auth/passkeys",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["passkeys"]) == 3


# ---------------------------------------------------------------------------
# WebAuthn config tests
# ---------------------------------------------------------------------------


class TestWebAuthnConfig:
    def test_production_requires_rp_id(self):
        s = Settings(env="production", rp_id="")
        with pytest.raises(RuntimeError, match="H4CKATH0N_RP_ID"):
            s.effective_rp_id()

    def test_production_requires_origin(self):
        s = Settings(env="production", origin="")
        with pytest.raises(RuntimeError, match="H4CKATH0N_ORIGIN"):
            s.effective_origin()

    def test_dev_defaults_rp_id(self):
        import warnings

        s = Settings(env="development")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            assert s.effective_rp_id() == "localhost"

    def test_dev_defaults_origin(self):
        import warnings

        s = Settings(env="development")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            assert s.effective_origin() == "http://localhost:8000"

    def test_custom_rp_id(self):
        s = Settings(env="production", rp_id="example.com")
        assert s.effective_rp_id() == "example.com"


# ---------------------------------------------------------------------------
# Password auth disabled by default
# ---------------------------------------------------------------------------


class TestPasswordAuthDisabled:
    def test_password_routes_not_mounted_by_default(self, client: TestClient):
        r = client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "P@ss1"},
        )
        # Should return 404 or 405 since password routes are not mounted
        assert r.status_code in (404, 405)

    def test_password_login_not_mounted_by_default(self, client: TestClient):
        r = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "P@ss1"},
        )
        assert r.status_code in (404, 405)

    def test_password_reset_not_mounted_by_default(self, client: TestClient):
        r = client.post(
            "/auth/password-reset/request",
            json={"email": "test@example.com"},
        )
        assert r.status_code in (404, 405)
