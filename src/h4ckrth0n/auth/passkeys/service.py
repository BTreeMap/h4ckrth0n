"""Passkey (WebAuthn) business logic – challenge lifecycle, credential management."""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from h4ckrth0n.auth.models import User, WebAuthnChallenge, WebAuthnCredential
from h4ckrth0n.auth.passkeys.ids import new_key_id, new_user_id
from h4ckrth0n.auth.passkeys.webauthn import (
    base64url_to_bytes,
    bytes_to_base64url,
    make_authentication_options,
    make_registration_options,
    verify_authentication,
    verify_registration,
)
from h4ckrth0n.config import Settings


class LastPasskeyError(Exception):
    """Raised when an operation would leave a user with no active passkeys."""


# ---------------------------------------------------------------------------
# Challenge helpers
# ---------------------------------------------------------------------------


def _new_flow_id() -> str:
    return secrets.token_urlsafe(32)


def _new_challenge() -> bytes:
    return secrets.token_bytes(32)


def _get_valid_flow(db: Session, flow_id: str, kind: str) -> WebAuthnChallenge:
    """Fetch and validate an unconsumed, non-expired flow."""
    flow = db.query(WebAuthnChallenge).filter(WebAuthnChallenge.id == flow_id).first()
    if flow is None:
        raise ValueError("Unknown flow")
    if flow.kind != kind:
        raise ValueError("Flow kind mismatch")
    if flow.consumed_at is not None:
        raise ValueError("Flow already consumed")
    exp = flow.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)
    if exp < datetime.now(UTC):
        raise ValueError("Flow expired")
    return flow


def _consume_flow(db: Session, flow: WebAuthnChallenge) -> None:
    flow.consumed_at = datetime.now(UTC)
    db.flush()


# ---------------------------------------------------------------------------
# Registration (unauthenticated – creates a new account)
# ---------------------------------------------------------------------------


def start_registration(
    db: Session,
    settings: Settings,
) -> tuple[str, dict]:
    """Begin passkey registration – create user + flow, return (flow_id, options_dict)."""
    rp_id = settings.effective_rp_id()
    origin = settings.effective_origin()

    user = User()
    db.add(user)
    db.flush()

    challenge_bytes = _new_challenge()
    flow_id = _new_flow_id()
    flow = WebAuthnChallenge(
        id=flow_id,
        challenge=bytes_to_base64url(challenge_bytes),
        user_id=user.id,
        kind="register",
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.webauthn_ttl_seconds),
        rp_id=rp_id,
        origin=origin,
    )
    db.add(flow)
    db.commit()

    options = make_registration_options(
        rp_id=rp_id,
        rp_name=rp_id,
        user_id=user.id.encode("utf-8"),
        user_name=user.id,
        user_display_name=user.id,
        challenge=challenge_bytes,
        settings=settings,
    )
    return flow_id, options


def finish_registration(
    db: Session,
    flow_id: str,
    credential_json: dict,
    settings: Settings,
) -> User:
    """Complete passkey registration – verify attestation, store credential, return user."""
    flow = _get_valid_flow(db, flow_id, "register")

    challenge_bytes = base64url_to_bytes(flow.challenge)
    cred_id_bytes, public_key, sign_count, aaguid = verify_registration(
        credential_json=credential_json,
        expected_challenge=challenge_bytes,
        expected_rp_id=flow.rp_id,
        expected_origin=flow.origin,
    )

    _consume_flow(db, flow)

    transports = credential_json.get("response", {}).get("transports")
    cred = WebAuthnCredential(
        id=new_key_id(),
        user_id=flow.user_id,  # type: ignore[arg-type]
        credential_id=bytes_to_base64url(cred_id_bytes),
        public_key=public_key,
        sign_count=sign_count,
        aaguid=aaguid,
        transports=json.dumps(transports) if transports else None,
    )
    db.add(cred)
    db.commit()

    user = db.query(User).filter(User.id == flow.user_id).first()
    if user is None:
        raise ValueError("User not found")
    return user


# ---------------------------------------------------------------------------
# Authentication (unauthenticated – username-less)
# ---------------------------------------------------------------------------


def start_authentication(
    db: Session,
    settings: Settings,
) -> tuple[str, dict]:
    """Begin passkey login – return (flow_id, options_dict)."""
    rp_id = settings.effective_rp_id()
    origin = settings.effective_origin()

    challenge_bytes = _new_challenge()
    flow_id = _new_flow_id()
    flow = WebAuthnChallenge(
        id=flow_id,
        challenge=bytes_to_base64url(challenge_bytes),
        user_id=None,
        kind="authenticate",
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.webauthn_ttl_seconds),
        rp_id=rp_id,
        origin=origin,
    )
    db.add(flow)
    db.commit()

    options = make_authentication_options(
        rp_id=rp_id,
        challenge=challenge_bytes,
        settings=settings,
    )
    return flow_id, options


def finish_authentication(
    db: Session,
    flow_id: str,
    credential_json: dict,
    settings: Settings,
) -> User:
    """Complete passkey login – verify assertion, update counters, return user."""
    flow = _get_valid_flow(db, flow_id, "authenticate")

    raw_id = credential_json.get("rawId") or credential_json.get("id", "")
    stored = (
        db.query(WebAuthnCredential)
        .filter(
            WebAuthnCredential.credential_id == raw_id,
            WebAuthnCredential.revoked_at.is_(None),
        )
        .first()
    )
    if stored is None:
        raise ValueError("Unknown or revoked credential")

    challenge_bytes = base64url_to_bytes(flow.challenge)
    _cred_id, new_sign_count = verify_authentication(
        credential_json=credential_json,
        expected_challenge=challenge_bytes,
        expected_rp_id=flow.rp_id,
        expected_origin=flow.origin,
        credential_public_key=stored.public_key,
        credential_current_sign_count=stored.sign_count,
    )

    _consume_flow(db, flow)

    stored.sign_count = new_sign_count
    stored.last_used_at = datetime.now(UTC)
    db.commit()

    user = db.query(User).filter(User.id == stored.user_id).first()
    if user is None:
        raise ValueError("User not found")
    return user


# ---------------------------------------------------------------------------
# Add credential (authenticated)
# ---------------------------------------------------------------------------


def start_add_credential(
    db: Session,
    user: User,
    settings: Settings,
) -> tuple[str, dict]:
    """Begin adding a passkey for an already-authenticated user."""
    rp_id = settings.effective_rp_id()
    origin = settings.effective_origin()

    # Build excludeCredentials from user's existing active credentials
    existing = (
        db.query(WebAuthnCredential)
        .filter(
            WebAuthnCredential.user_id == user.id,
            WebAuthnCredential.revoked_at.is_(None),
        )
        .all()
    )
    from webauthn.helpers.structs import PublicKeyCredentialDescriptor

    exclude = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id))
        for c in existing
    ]

    challenge_bytes = _new_challenge()
    flow_id = _new_flow_id()
    flow = WebAuthnChallenge(
        id=flow_id,
        challenge=bytes_to_base64url(challenge_bytes),
        user_id=user.id,
        kind="add_credential",
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.webauthn_ttl_seconds),
        rp_id=rp_id,
        origin=origin,
    )
    db.add(flow)
    db.commit()

    options = make_registration_options(
        rp_id=rp_id,
        rp_name=rp_id,
        user_id=user.id.encode("utf-8"),
        user_name=user.id,
        user_display_name=user.id,
        challenge=challenge_bytes,
        settings=settings,
        exclude_credentials=exclude,
    )
    return flow_id, options


def finish_add_credential(
    db: Session,
    flow_id: str,
    credential_json: dict,
    current_user: User,
    settings: Settings,
) -> WebAuthnCredential:
    """Complete adding a passkey – verify attestation, store credential."""
    flow = _get_valid_flow(db, flow_id, "add_credential")
    if flow.user_id != current_user.id:
        raise ValueError("Flow does not belong to current user")

    challenge_bytes = base64url_to_bytes(flow.challenge)
    cred_id_bytes, public_key, sign_count, aaguid = verify_registration(
        credential_json=credential_json,
        expected_challenge=challenge_bytes,
        expected_rp_id=flow.rp_id,
        expected_origin=flow.origin,
    )

    _consume_flow(db, flow)

    transports = credential_json.get("response", {}).get("transports")
    cred = WebAuthnCredential(
        id=new_key_id(),
        user_id=current_user.id,
        credential_id=bytes_to_base64url(cred_id_bytes),
        public_key=public_key,
        sign_count=sign_count,
        aaguid=aaguid,
        transports=json.dumps(transports) if transports else None,
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


# ---------------------------------------------------------------------------
# List & Revoke
# ---------------------------------------------------------------------------


def list_passkeys(db: Session, user: User) -> list[WebAuthnCredential]:
    """List all credentials (active and revoked) for a user."""
    return (
        db.query(WebAuthnCredential)
        .filter(WebAuthnCredential.user_id == user.id)
        .order_by(WebAuthnCredential.created_at)
        .all()
    )


def revoke_passkey(db: Session, user: User, key_id: str) -> None:
    """Revoke a credential by its internal key id.

    Raises ``LastPasskeyError`` if this is the user's last active passkey.
    Uses ``with_for_update()`` for transactional safety in Postgres.
    """
    cred = (
        db.query(WebAuthnCredential)
        .filter(
            WebAuthnCredential.id == key_id,
            WebAuthnCredential.user_id == user.id,
        )
        .first()
    )
    if cred is None:
        raise ValueError("Credential not found")
    if cred.revoked_at is not None:
        raise ValueError("Credential already revoked")

    # Count active (non-revoked) passkeys with row-level locking for concurrency safety.
    # For SQLite (dev), with_for_update is silently ignored which is acceptable.
    active_count = (
        db.query(WebAuthnCredential)
        .filter(
            WebAuthnCredential.user_id == user.id,
            WebAuthnCredential.revoked_at.is_(None),
        )
        .with_for_update()
        .count()
    )
    if active_count <= 1:
        raise LastPasskeyError(
            "Cannot revoke the last active passkey. Add another passkey first."
        )

    cred.revoked_at = datetime.now(UTC)
    db.commit()


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def cleanup_expired_challenges(db: Session) -> int:
    """Delete expired and consumed challenges. Returns count deleted."""
    now = datetime.now(UTC)
    count = (
        db.query(WebAuthnChallenge)
        .filter(WebAuthnChallenge.expires_at < now)
        .delete(synchronize_session=False)
    )
    db.commit()
    return count  # type: ignore[return-value]
