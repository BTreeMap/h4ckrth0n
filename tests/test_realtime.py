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
def app(settings):
    return create_app(settings)


@pytest.fixture()
def db_session(app):
    session = app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def _seed_user_and_device(db_session) -> tuple[str, str, bytes]:
    """Insert a user + device directly in DB. Returns (user_id, device_id, private_pem)."""
    private_pem, jwk_dict = _create_device_keypair()
    uid = new_user_id()
    did = new_device_id()
    user = User(id=uid, role="user")
    device = Device(id=did, user_id=uid, public_key_jwk=json.dumps(jwk_dict))
    db_session.add(user)
    db_session.add(device)
    db_session.commit()
    return uid, did, private_pem


# ---------------------------------------------------------------------------
# verify_device_jwt
# ---------------------------------------------------------------------------


class TestVerifyDeviceJwt:
    def test_valid_http_aud(self, db_session):
        uid, did, pem = _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_HTTP)
        ctx = verify_device_jwt(token, expected_aud=AUD_HTTP, db=db_session)
        assert ctx.user_id == uid
        assert ctx.device_id == did

    def test_valid_ws_aud(self, db_session):
        uid, did, pem = _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_WS)
        ctx = verify_device_jwt(token, expected_aud=AUD_WS, db=db_session)
        assert ctx.user_id == uid

    def test_valid_sse_aud(self, db_session):
        uid, did, pem = _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_SSE)
        ctx = verify_device_jwt(token, expected_aud=AUD_SSE, db=db_session)
        assert ctx.user_id == uid

    def test_wrong_aud_rejected(self, db_session):
        uid, did, pem = _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_HTTP)
        with pytest.raises(AuthError, match="Invalid aud"):
            verify_device_jwt(token, expected_aud=AUD_WS, db=db_session)

    def test_missing_aud_rejected(self, db_session):
        uid, did, pem = _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=None)
        with pytest.raises(AuthError, match="Missing aud"):
            verify_device_jwt(token, expected_aud=AUD_HTTP, db=db_session)

    def test_expired_token_rejected(self, db_session):
        uid, did, pem = _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_HTTP, expire_minutes=-1)
        with pytest.raises(AuthError, match="Token expired"):
            verify_device_jwt(token, expected_aud=AUD_HTTP, db=db_session)

    def test_unknown_device_rejected(self, db_session):
        pem, _jwk = _create_device_keypair()
        token = _make_token("u" + "a" * 31, "d" + "a" * 31, pem, aud=AUD_HTTP)
        with pytest.raises(AuthError, match="Unknown device"):
            verify_device_jwt(token, expected_aud=AUD_HTTP, db=db_session)

    def test_http_aud_rejected_for_ws(self, db_session):
        """HTTP token must not work for WebSocket."""
        uid, did, pem = _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_HTTP)
        with pytest.raises(AuthError, match="Invalid aud"):
            verify_device_jwt(token, expected_aud=AUD_WS, db=db_session)

    def test_ws_aud_rejected_for_sse(self, db_session):
        """WS token must not work for SSE."""
        uid, did, pem = _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_WS)
        with pytest.raises(AuthError, match="Invalid aud"):
            verify_device_jwt(token, expected_aud=AUD_SSE, db=db_session)


# ---------------------------------------------------------------------------
# HTTP endpoint with aud enforcement
# ---------------------------------------------------------------------------


class TestHttpAudEnforcement:
    def test_http_aud_accepted(self, app, db_session, client=None):
        from h4ckath0n.auth import require_user

        @app.get("/rt-test")
        def rt_test(user=require_user()):
            return {"id": user.id}

        c = TestClient(app)
        uid, did, pem = _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_HTTP)
        r = c.get("/rt-test", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_ws_aud_rejected_for_http(self, app, db_session):
        from h4ckath0n.auth import require_user

        @app.get("/rt-test2")
        def rt_test2(user=require_user()):
            return {"id": user.id}

        c = TestClient(app)
        uid, did, pem = _seed_user_and_device(db_session)
        token = _make_token(uid, did, pem, aud=AUD_WS)
        r = c.get("/rt-test2", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401
