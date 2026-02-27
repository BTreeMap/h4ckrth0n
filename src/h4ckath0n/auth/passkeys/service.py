"""Passkey (WebAuthn) business logic - challenge lifecycle, credential management."""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from h4ckath0n.auth.models import User, WebAuthnChallenge, WebAuthnCredential
from h4ckath0n.auth.passkeys.ids import new_key_id
from h4ckath0n.auth.passkeys.webauthn import (
    base64url_to_bytes,
    bytes_to_base64url,
    make_authentication_options,
    make_registration_options,
    verify_authentication,
    verify_registration,
)
from h4ckath0n.config import Settings


class LastPasskeyError(Exception):
    """Raised when attempting to revoke the last active passkey, which would prevent user login."""


# ---------------------------------------------------------------------------
# Challenge helpers
# ---------------------------------------------------------------------------


def _new_flow_id() -> str:
    return secrets.token_urlsafe(32)


def _new_challenge() -> bytes:
    return secrets.token_bytes(32)


async def _get_valid_flow(db: AsyncSession, flow_id: str, kind: str) -> WebAuthnChallenge:
    """Fetch and validate an unconsumed, non-expired flow."""
    result = await db.execute(select(WebAuthnChallenge).filter(WebAuthnChallenge.id == flow_id))
    if (flow := result.scalars().first()) is None:
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


async def _consume_flow(db: AsyncSession, flow: WebAuthnChallenge) -> None:
    flow.consumed_at = datetime.now(UTC)
    await db.flush()


# ---------------------------------------------------------------------------
# Registration (unauthenticated - creates a new account)
# ---------------------------------------------------------------------------


async def start_registration(
    db: AsyncSession,
    settings: Settings,
) -> tuple[str, dict]:
    """Begin passkey registration - create user + flow, return (flow_id, options_dict)."""
    rp_id = settings.effective_rp_id()
    origin = settings.effective_origin()

    user = User()
    db.add(user)
    await db.flush()

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
    await db.commit()

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


async def finish_registration(
    db: AsyncSession,
    flow_id: str,
    credential_json: dict,
    settings: Settings,
) -> User:
    """Complete passkey registration - verify attestation, store credential, return user."""
    flow = await _get_valid_flow(db, flow_id, "register")

    challenge_bytes = base64url_to_bytes(flow.challenge)
    cred_id_bytes, public_key, sign_count, aaguid = verify_registration(
        credential_json=credential_json,
        expected_challenge=challenge_bytes,
        expected_rp_id=flow.rp_id,
        expected_origin=flow.origin,
    )

    await _consume_flow(db, flow)

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
    await db.commit()

    result = await db.execute(select(User).filter(User.id == flow.user_id))
    if (user := result.scalars().first()) is None:
        raise ValueError("User not found")
    return user


# ---------------------------------------------------------------------------
# Authentication (unauthenticated - username-less)
# ---------------------------------------------------------------------------


async def start_authentication(
    db: AsyncSession,
    settings: Settings,
) -> tuple[str, dict]:
    """Begin passkey login - return (flow_id, options_dict)."""
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
    await db.commit()

    options = make_authentication_options(
        rp_id=rp_id,
        challenge=challenge_bytes,
        settings=settings,
    )
    return flow_id, options


async def finish_authentication(
    db: AsyncSession,
    flow_id: str,
    credential_json: dict,
    settings: Settings,
) -> User:
    """Complete passkey login - verify assertion, update counters, return user."""
    flow = await _get_valid_flow(db, flow_id, "authenticate")

    raw_id = credential_json.get("rawId") or credential_json.get("id", "")
    result = await db.execute(
        select(WebAuthnCredential).filter(
            WebAuthnCredential.credential_id == raw_id,
            WebAuthnCredential.revoked_at.is_(None),
        )
    )
    if (stored := result.scalars().first()) is None:
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

    await _consume_flow(db, flow)

    stored.sign_count = new_sign_count
    stored.last_used_at = datetime.now(UTC)
    await db.commit()

    user_result = await db.execute(select(User).filter(User.id == stored.user_id))
    if (user := user_result.scalars().first()) is None:
        raise ValueError("User not found")
    return user


# ---------------------------------------------------------------------------
# Add credential (authenticated)
# ---------------------------------------------------------------------------


async def start_add_credential(
    db: AsyncSession,
    user: User,
    settings: Settings,
) -> tuple[str, dict]:
    """Begin adding a passkey for an already-authenticated user."""
    rp_id = settings.effective_rp_id()
    origin = settings.effective_origin()

    # Build excludeCredentials from user's existing active credentials
    result = await db.execute(
        select(WebAuthnCredential).filter(
            WebAuthnCredential.user_id == user.id,
            WebAuthnCredential.revoked_at.is_(None),
        )
    )
    existing = result.scalars().all()
    from webauthn.helpers.structs import PublicKeyCredentialDescriptor

    exclude = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id)) for c in existing
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
    await db.commit()

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


async def finish_add_credential(
    db: AsyncSession,
    flow_id: str,
    credential_json: dict,
    current_user: User,
    settings: Settings,
) -> WebAuthnCredential:
    """Complete adding a passkey - verify attestation, store credential."""
    flow = await _get_valid_flow(db, flow_id, "add_credential")
    if flow.user_id != current_user.id:
        raise ValueError("Flow does not belong to current user")

    challenge_bytes = base64url_to_bytes(flow.challenge)
    cred_id_bytes, public_key, sign_count, aaguid = verify_registration(
        credential_json=credential_json,
        expected_challenge=challenge_bytes,
        expected_rp_id=flow.rp_id,
        expected_origin=flow.origin,
    )

    await _consume_flow(db, flow)

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
    await db.commit()
    await db.refresh(cred)
    return cred


# ---------------------------------------------------------------------------
# List & Revoke
# ---------------------------------------------------------------------------


async def list_passkeys(db: AsyncSession, user: User) -> list[WebAuthnCredential]:
    """List all credentials (active and revoked) for a user."""
    result = await db.execute(
        select(WebAuthnCredential)
        .filter(WebAuthnCredential.user_id == user.id)
        .order_by(WebAuthnCredential.created_at)
    )
    return list(result.scalars().all())


async def rename_passkey(
    db: AsyncSession, user: User, key_id: str, name: str | None
) -> WebAuthnCredential:
    """Rename a passkey. *name* is trimmed; empty-after-trim stored as NULL.

    Raises ValueError if not found / not owned / revoked.
    """
    result = await db.execute(
        select(WebAuthnCredential).filter(
            WebAuthnCredential.id == key_id,
            WebAuthnCredential.user_id == user.id,
        )
    )
    if (cred := result.scalars().first()) is None:
        raise ValueError("Credential not found")
    if cred.revoked_at is not None:
        raise ValueError("Cannot rename a revoked passkey")

    clean: str | None = name.strip() if name else None
    if clean == "":
        clean = None
    if clean is not None and len(clean) > 64:
        raise ValueError("Name must be 64 characters or fewer")

    cred.name = clean
    await db.commit()
    await db.refresh(cred)
    return cred


async def revoke_passkey(db: AsyncSession, user: User, key_id: str) -> None:
    """Revoke a credential by its internal key id.

    Raises LastPasskeyError if this is the user's last active passkey.

    Concurrency and Postgres:
    - Postgres forbids FOR UPDATE with aggregate functions like COUNT(*).
    - To serialize "last passkey" checks, we use a per-user row lock on User.
      That acts as a mutex for passkey mutations per user.
    """
    try:
        # Per-user mutex. In SQLite, FOR UPDATE is ignored (acceptable for dev/tests).
        await db.execute(select(User.id).filter(User.id == user.id).with_for_update())

        result = await db.execute(
            select(WebAuthnCredential).filter(
                WebAuthnCredential.id == key_id,
                WebAuthnCredential.user_id == user.id,
            )
        )
        if (cred := result.scalars().first()) is None:
            raise ValueError("Credential not found")
        if cred.revoked_at is not None:
            raise ValueError("Credential already revoked")

        # Count active passkeys without FOR UPDATE (mutex is the User row lock above).
        active_count = await db.scalar(
            select(func.count())
            .select_from(WebAuthnCredential)
            .filter(
                WebAuthnCredential.user_id == user.id,
                WebAuthnCredential.revoked_at.is_(None),
            )
        )
        if active_count is not None and int(active_count) <= 1:
            raise LastPasskeyError(
                "Cannot revoke the last active passkey. "
                "Add another passkey via POST /auth/passkey/add/start first."
            )

        cred.revoked_at = datetime.now(UTC)
        await db.commit()
    except Exception:
        # Ensure any open transaction is rolled back so row locks are released promptly.
        await db.rollback()
        raise


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


async def cleanup_expired_challenges(db: AsyncSession) -> int:
    """Delete expired and consumed challenges. Returns count deleted."""
    from sqlalchemy import delete

    now = datetime.now(UTC)
    result = await db.execute(delete(WebAuthnChallenge).filter(WebAuthnChallenge.expires_at < now))
    await db.commit()
    count: int = result.rowcount  # type: ignore[attr-defined]
    return count
