"""Tests for realtime auth helpers – aud enforcement and transport verification."""

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
from sqlalchemy.ext.asyncio import AsyncSession

from h4ckath0n.app import create_app
from h4ckath0n.auth.models import Device, User
from h4ckath0n.auth.passkeys.ids import new_device_id, new_user_id
from h4ckath0n.config import Settings
from h4ckath0n.realtime.auth import (
    AUD_HTTP,
    AUD_SSE,
    AUD_WS,
    AuthError,
    verify_device_jwt,
)


def _create_device_keypair() -> tuple[bytes, dict]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    public_key = private_key.public_key()
    jwk_dict = json.loads(ECAlgorithm(ECAlgorithm.SHA256).to_jwk(public_key))
    return private_pem, jwk_dict


def _make_token(
    user_id: str,
    device_id: str,
    private_pem: bytes,
    aud: str | None = None,
    expire_minutes: int = 15,
) -> str:
    import jwt as pyjwt

    now = datetime.now(UTC)
    payload: dict = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
    }
    if aud is not None:
        payload["aud"] = aud
    return pyjwt.encode(
        payload,
        private_pem,
        algorithm="ES256",
        headers={"kid": device_id},
    )


@pytest.fixture()
def settings(tmp_path):
    db_path = tmp_path / "rt_test.db"
    return Settings(
        database_url=f"sqlite:///{db_path}",
        env="development",
        password_auth_enabled=False,
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
async def db_session(app):
    # Need to trigger lifespan first via TestClient context
    async with app.state.async_session_factory() as session:
        yield session


async def _seed_user_and_device(db_session: AsyncSession) -> tuple[str, str, bytes]:
    """Insert a user + device directly in DB. Returns (user_id, device_id, private_pem)."""
    private_pem, jwk_dict = _create_device_keypair()
    uid = new_user_id()
    did = new_device_id()
    user = User(id=uid, role="user")
    from h4ckath0n.auth.service import _jwk_fingerprint

    fp = _jwk_fingerprint(jwk_dict)
    device = Device(id=did, user_id=uid, public_key_jwk=json.dumps(jwk_dict), fingerprint=fp)
    db_session.add(user)
    db_session.add(device)
    await db_session.commit()
    return uid, did, private_pem


# ---------------------------------------------------------------------------
# verify_device_jwt
# ---------------------------------------------------------------------------


class TestVerifyDeviceJwt:
    async def test_valid_http_aud(self, db_session: AsyncSession):
        uid, did, pem = await _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_HTTP)
        ctx = await verify_device_jwt(token, expected_aud=AUD_HTTP, db=db_session)
        assert ctx.user_id == uid
        assert ctx.device_id == did

    async def test_valid_ws_aud(self, db_session: AsyncSession):
        uid, did, pem = await _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_WS)
        ctx = await verify_device_jwt(token, expected_aud=AUD_WS, db=db_session)
        assert ctx.user_id == uid

    async def test_valid_sse_aud(self, db_session: AsyncSession):
        uid, did, pem = await _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_SSE)
        ctx = await verify_device_jwt(token, expected_aud=AUD_SSE, db=db_session)
        assert ctx.user_id == uid

    async def test_wrong_aud_rejected(self, db_session: AsyncSession):
        uid, did, pem = await _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_HTTP)
        with pytest.raises(AuthError, match="Invalid aud"):
            await verify_device_jwt(token, expected_aud=AUD_WS, db=db_session)

    async def test_missing_aud_rejected(self, db_session: AsyncSession):
        uid, did, pem = await _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=None)
        with pytest.raises(AuthError, match="Missing aud"):
            await verify_device_jwt(token, expected_aud=AUD_HTTP, db=db_session)

    async def test_expired_token_rejected(self, db_session: AsyncSession):
        uid, did, pem = await _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_HTTP, expire_minutes=-1)
        with pytest.raises(AuthError, match="Token expired"):
            await verify_device_jwt(token, expected_aud=AUD_HTTP, db=db_session)

    async def test_unknown_device_rejected(self, db_session: AsyncSession):
        pem, _jwk = _create_device_keypair()
        token = _make_token("u" + "a" * 31, "d" + "a" * 31, pem, aud=AUD_HTTP)
        with pytest.raises(AuthError, match="Unknown device"):
            await verify_device_jwt(token, expected_aud=AUD_HTTP, db=db_session)

    async def test_http_aud_rejected_for_ws(self, db_session: AsyncSession):
        """HTTP token must not work for WebSocket."""
        uid, did, pem = await _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_HTTP)
        with pytest.raises(AuthError, match="Invalid aud"):
            await verify_device_jwt(token, expected_aud=AUD_WS, db=db_session)

    async def test_ws_aud_rejected_for_sse(self, db_session: AsyncSession):
        """WS token must not work for SSE."""
        uid, did, pem = await _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_WS)
        with pytest.raises(AuthError, match="Invalid aud"):
            await verify_device_jwt(token, expected_aud=AUD_SSE, db=db_session)


# ---------------------------------------------------------------------------
# HTTP endpoint with aud enforcement
# ---------------------------------------------------------------------------


class TestHttpAudEnforcement:
    async def test_http_aud_accepted(self, app, db_session: AsyncSession, client=None):
        from h4ckath0n.auth import require_user

        @app.get("/rt-test")
        def rt_test(user=require_user()):
            return {"id": user.id}

        with TestClient(app) as c:
            uid, did, pem = await _seed_user_and_device(db_session)
            token = _make_token(uid, did, pem, aud=AUD_HTTP)
            r = c.get("/rt-test", headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 200

    async def test_ws_aud_rejected_for_http(self, app, db_session: AsyncSession):
        from h4ckath0n.auth import require_user

        @app.get("/rt-test2")
        def rt_test2(user=require_user()):
            return {"id": user.id}

        with TestClient(app) as c:
            uid, did, pem = await _seed_user_and_device(db_session)
            token = _make_token(uid, did, pem, aud=AUD_WS)
            r = c.get("/rt-test2", headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 401


# ---------------------------------------------------------------------------
# Stable device identity
# ---------------------------------------------------------------------------


class TestStableDeviceIdentity:
    """register_device() must reuse the same device_id for the same JWK."""

    async def test_same_jwk_returns_same_device_id(self, db_session: AsyncSession):
        from h4ckath0n.auth.service import register_device

        _pem, jwk = _create_device_keypair()
        uid = new_user_id()
        db_session.add(User(id=uid, role="user"))
        await db_session.commit()

        did1 = await register_device(db_session, uid, jwk, "first")
        did2 = await register_device(db_session, uid, jwk, "second")
        assert did1 == did2
        assert did1.startswith("d")

    async def test_different_jwk_gets_different_device_id(self, db_session: AsyncSession):
        from h4ckath0n.auth.service import register_device

        _pem1, jwk1 = _create_device_keypair()
        _pem2, jwk2 = _create_device_keypair()
        uid = new_user_id()
        db_session.add(User(id=uid, role="user"))
        await db_session.commit()

        did1 = await register_device(db_session, uid, jwk1, "a")
        did2 = await register_device(db_session, uid, jwk2, "b")
        assert did1 != did2

    async def test_no_jwk_returns_empty_string(self, db_session: AsyncSession):
        from h4ckath0n.auth.service import register_device

        uid = new_user_id()
        db_session.add(User(id=uid, role="user"))
        await db_session.commit()

        assert await register_device(db_session, uid, None) == ""


# ---------------------------------------------------------------------------
# Revoked device
# ---------------------------------------------------------------------------


class TestRevokedDevice:
    """Tokens signed by a revoked device must be rejected."""

    async def test_revoked_device_rejected(self, db_session: AsyncSession):
        uid, did, pem = await _seed_user_and_device(db_session)
        from sqlalchemy import select

        result = await db_session.execute(select(Device).filter(Device.id == did))
        device = result.scalars().one()
        device.revoked_at = datetime.now(UTC)
        await db_session.commit()

        token = _make_token(uid, did, pem, aud=AUD_HTTP)
        with pytest.raises(AuthError, match="Device revoked"):
            await verify_device_jwt(token, expected_aud=AUD_HTTP, db=db_session)

    async def test_non_revoked_device_accepted(self, db_session: AsyncSession):
        uid, did, pem = await _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_HTTP)
        ctx = await verify_device_jwt(token, expected_aud=AUD_HTTP, db=db_session)
        assert ctx.device_id == did
