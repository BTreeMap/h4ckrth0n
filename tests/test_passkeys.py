"""Tests for passkey (WebAuthn) authentication.

Covers:
- ID generator tests (length, prefix, charset)
- Flow state tests (expiry, consumed flows)
- Last-passkey invariant (revoking only credential blocked, multiple ok, concurrency)
- Route wiring and DB persistence
- WebAuthn config (production requires rp_id/origin)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

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
        auth_signing_key="test-secret-key-for-unit-tests-minimum-32-bytes",
        env="development",
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
    def test_register_start_creates_flow(self, db_session, settings):
        flow_id, options = start_registration(db_session, settings)
        assert flow_id
        assert "challenge" in options
        flow = db_session.query(WebAuthnChallenge).filter_by(id=flow_id).first()
        assert flow is not None
        assert flow.kind == "register"
        assert flow.consumed_at is None

    def test_register_start_creates_user(self, db_session, settings):
        flow_id, _ = start_registration(db_session, settings)
        flow = db_session.query(WebAuthnChallenge).filter_by(id=flow_id).first()
        user = db_session.query(User).filter_by(id=flow.user_id).first()
        assert user is not None
        assert is_user_id(user.id)

    def test_authentication_start_creates_flow(self, db_session, settings):
        flow_id, options = start_authentication(db_session, settings)
        assert flow_id
        assert "challenge" in options
        flow = db_session.query(WebAuthnChallenge).filter_by(id=flow_id).first()
        assert flow is not None
        assert flow.kind == "authenticate"
        assert flow.user_id is None  # username-less

    def test_expired_flow_rejected(self, db_session, settings):
        from h4ckath0n.auth.passkeys.service import _get_valid_flow

        flow_id, _ = start_registration(db_session, settings)
        # Manually expire the flow
        flow = db_session.query(WebAuthnChallenge).filter_by(id=flow_id).first()
        flow.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db_session.commit()

        with pytest.raises(ValueError, match="expired"):
            _get_valid_flow(db_session, flow_id, "register")

    def test_consumed_flow_rejected(self, db_session, settings):
        from h4ckath0n.auth.passkeys.service import _consume_flow, _get_valid_flow

        flow_id, _ = start_registration(db_session, settings)
        flow = db_session.query(WebAuthnChallenge).filter_by(id=flow_id).first()
        _consume_flow(db_session, flow)
        db_session.commit()

        with pytest.raises(ValueError, match="consumed"):
            _get_valid_flow(db_session, flow_id, "register")

    def test_flow_kind_mismatch_rejected(self, db_session, settings):
        from h4ckath0n.auth.passkeys.service import _get_valid_flow

        flow_id, _ = start_registration(db_session, settings)
        with pytest.raises(ValueError, match="mismatch"):
            _get_valid_flow(db_session, flow_id, "authenticate")

    def test_cleanup_expired_challenges(self, db_session, settings):
        flow_id, _ = start_registration(db_session, settings)
        # Expire it
        flow = db_session.query(WebAuthnChallenge).filter_by(id=flow_id).first()
        flow.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db_session.commit()

        deleted = cleanup_expired_challenges(db_session)
        assert deleted >= 1

        remaining = db_session.query(WebAuthnChallenge).filter_by(id=flow_id).first()
        assert remaining is None


# ---------------------------------------------------------------------------
# Last-passkey invariant
# ---------------------------------------------------------------------------


class TestLastPasskeyInvariant:
    def _create_user_with_passkeys(self, db_session, count=1):
        """Helper to create a user with *count* active passkeys."""
        user = User()
        db_session.add(user)
        db_session.flush()

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
        db_session.commit()
        for c in creds:
            db_session.refresh(c)
        db_session.refresh(user)
        return user, creds

    def test_revoke_only_credential_blocked(self, db_session):
        user, creds = self._create_user_with_passkeys(db_session, count=1)
        with pytest.raises(LastPasskeyError, match="last active passkey"):
            revoke_passkey(db_session, user, creds[0].id)

    def test_revoke_one_of_two_allowed(self, db_session):
        user, creds = self._create_user_with_passkeys(db_session, count=2)
        revoke_passkey(db_session, user, creds[0].id)
        # Credential should now be revoked
        db_session.refresh(creds[0])
        assert creds[0].revoked_at is not None

    def test_revoke_down_to_one_then_blocked(self, db_session):
        user, creds = self._create_user_with_passkeys(db_session, count=2)
        revoke_passkey(db_session, user, creds[0].id)
        # Now only one active – should block
        with pytest.raises(LastPasskeyError):
            revoke_passkey(db_session, user, creds[1].id)

    def test_revoke_already_revoked_raises(self, db_session):
        user, creds = self._create_user_with_passkeys(db_session, count=2)
        revoke_passkey(db_session, user, creds[0].id)
        with pytest.raises(ValueError, match="already revoked"):
            revoke_passkey(db_session, user, creds[0].id)

    def test_revoke_nonexistent_raises(self, db_session):
        user, _ = self._create_user_with_passkeys(db_session, count=1)
        with pytest.raises(ValueError, match="not found"):
            revoke_passkey(db_session, user, "knonexistent00000000000000000000")

    def test_revoke_other_users_credential_fails(self, db_session):
        user1, creds1 = self._create_user_with_passkeys(db_session, count=2)
        user2, creds2 = self._create_user_with_passkeys(db_session, count=2)
        with pytest.raises(ValueError, match="not found"):
            revoke_passkey(db_session, user1, creds2[0].id)

    def test_list_passkeys(self, db_session):
        user, creds = self._create_user_with_passkeys(db_session, count=3)
        listed = list_passkeys(db_session, user)
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

    def test_register_start_creates_user_in_db(self, client: TestClient, db_session):
        r = client.post("/auth/passkey/register/start")
        assert r.status_code == 200
        flow_id = r.json()["flow_id"]
        flow = db_session.query(WebAuthnChallenge).filter_by(id=flow_id).first()
        assert flow is not None
        user = db_session.query(User).filter_by(id=flow.user_id).first()
        assert user is not None
        assert is_user_id(user.id)


# ---------------------------------------------------------------------------
# Revoke route tests (via HTTP, using DB-seeded credentials)
# ---------------------------------------------------------------------------


class TestPasskeyRevokeRoute:
    def _setup_user_with_token(self, client, db_session, settings, n_creds=2):
        """Create a user with passkeys and return (user, creds, access_token)."""
        from h4ckath0n.auth.jwt import create_access_token

        user = User()
        db_session.add(user)
        db_session.flush()

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
        db_session.commit()
        for c in creds:
            db_session.refresh(c)
        db_session.refresh(user)

        token = create_access_token(
            user_id=user.id,
            role=user.role,
            scopes=[],
            signing_key=settings.effective_signing_key(),
            algorithm=settings.auth_algorithm,
            expire_minutes=settings.access_token_expire_minutes,
        )
        return user, creds, token

    def test_revoke_one_of_two_via_route(self, client, db_session, settings):
        user, creds, token = self._setup_user_with_token(client, db_session, settings, 2)
        r = client.post(
            f"/auth/passkeys/{creds[0].id}/revoke",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200

    def test_revoke_last_passkey_blocked_via_route(self, client, db_session, settings):
        user, creds, token = self._setup_user_with_token(client, db_session, settings, 1)
        r = client.post(
            f"/auth/passkeys/{creds[0].id}/revoke",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 409
        body = r.json()
        assert body["detail"]["code"] == "LAST_PASSKEY"

    def test_list_passkeys_via_route(self, client, db_session, settings):
        user, creds, token = self._setup_user_with_token(client, db_session, settings, 3)
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
        s = Settings(env="production", rp_id="", auth_signing_key="x" * 32)
        with pytest.raises(RuntimeError, match="H4CKATH0N_RP_ID"):
            s.effective_rp_id()

    def test_production_requires_origin(self):
        s = Settings(env="production", origin="", auth_signing_key="x" * 32)
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
        s = Settings(env="production", rp_id="example.com", auth_signing_key="x" * 32)
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
