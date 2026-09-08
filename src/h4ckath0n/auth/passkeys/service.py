"""Passkey (WebAuthn) business logic - challenge lifecycle, credential management."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from h4ckath0n.auth.models import (
    ChallengeKind,
    User,
    WebAuthnChallenge,
    WebAuthnCredential,
)
from h4ckath0n.auth.passkeys.errors import (
    LastPasskeyError,
    PasskeyAlreadyRevokedError,
    PasskeyNotFoundError,
    PasskeyRevokedError,
)
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
from h4ckath0n.rng import random_bytes as _rng_bytes
from h4ckath0n.rng import token_urlsafe as _rng_urlsafe

__all__ = [
    "LastPasskeyError",
    "start_registration",
    "finish_registration",
    "start_authentication",
    "finish_authentication",
    "start_add_credential",
    "finish_add_credential",
    "list_passkeys",
    "rename_passkey",
    "revoke_passkey",
    "cleanup_expired_challenges",
]


def _new_flow_id() -> str:
    # 32 bytes → 256-bit unguessable URL-safe ID stored in the DB per flow.
    return _rng_urlsafe(32)


def _new_challenge() -> bytes:
    # WebAuthn spec requires ≥16 bytes; 32 gives 256-bit security margin.
    return _rng_bytes(32)


async def _get_valid_flow(
    db: AsyncSession, flow_id: str, kind: ChallengeKind
) -> WebAuthnChallenge:
    """Fetch and validate an unconsumed, non-expired flow."""
    # Use db.get() for primary key lookup.
    if (flow := await db.get(WebAuthnChallenge, flow_id)) is None:
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


async def start_registration(
    db: AsyncSession,
    settings: Settings,
    *,
    display_name: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Begin passkey registration - create user + flow, return (flow_id, options_dict)."""
    rp_id = settings.effective_rp_id()
    origin = settings.effective_origin()

    user = User(display_name=display_name)
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
        user_display_name=display_name or user.id,
        challenge=challenge_bytes,
        settings=settings,
    )
    return flow_id, options


async def finish_registration(
    db: AsyncSession,
    flow_id: str,
    credential_json: dict[str, Any],
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
        user_id=flow.user_id,
        credential_id=bytes_to_base64url(cred_id_bytes),
        public_key=public_key,
        sign_count=sign_count,
        aaguid=aaguid,
        transports=json.dumps(transports) if transports else None,
    )
    db.add(cred)
    await db.commit()

    # Use db.get() for primary key lookup.
    if (user := await db.get(User, flow.user_id)) is None:
        raise ValueError("User not found")
    return user


async def start_authentication(
    db: AsyncSession,
    settings: Settings,
) -> tuple[str, dict[str, Any]]:
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
    credential_json: dict[str, Any],
    settings: Settings,
) -> User:
    """Complete passkey login - verify assertion, update counters, return user."""
    flow = await _get_valid_flow(db, flow_id, "authenticate")

    raw_id = credential_json.get("rawId") or credential_json.get("id", "")
    # ⚡ Bolt: Use .scalar() instead of .execute().scalars().first() for performance
    stored = await db.scalar(
        select(WebAuthnCredential).filter(
            WebAuthnCredential.credential_id == raw_id,
            WebAuthnCredential.revoked_at.is_(None),
        )
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

    await _consume_flow(db, flow)

    stored.sign_count = new_sign_count
    stored.last_used_at = datetime.now(UTC)
    await db.commit()

    # Use db.get() for primary key lookup.
    if (user := await db.get(User, stored.user_id)) is None:
        raise ValueError("User not found")
    return user


async def start_add_credential(
    db: AsyncSession,
    user: User,
    settings: Settings,
) -> tuple[str, dict[str, Any]]:
    """Begin adding a passkey for an already-authenticated user."""
    rp_id = settings.effective_rp_id()
    origin = settings.effective_origin()

    # Exclude the user's active credentials.
    result = await db.execute(
        select(WebAuthnCredential).filter(
            WebAuthnCredential.user_id == user.id,
            WebAuthnCredential.revoked_at.is_(None),
        )
    )
    existing = result.scalars().all()
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
    await db.commit()

    options = make_registration_options(
        rp_id=rp_id,
        rp_name=rp_id,
        user_id=user.id.encode("utf-8"),
        user_name=user.id,
        user_display_name=user.display_name or user.id,
        challenge=challenge_bytes,
        settings=settings,
        exclude_credentials=exclude,
    )
    return flow_id, options


async def finish_add_credential(
    db: AsyncSession,
    flow_id: str,
    credential_json: dict[str, Any],
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

    Raises :class:`PasskeyNotFoundError` if not found / not owned and
    :class:`PasskeyRevokedError` if the credential is revoked.
    """
    if (cred := await db.get(WebAuthnCredential, key_id)) is None:
        raise PasskeyNotFoundError
    if cred.user_id != user.id:
        raise PasskeyNotFoundError
    if cred.revoked_at is not None:
        raise PasskeyRevokedError

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
        # Lock the user row as a per-user mutation mutex.
        await db.execute(select(User.id).filter(User.id == user.id).with_for_update())

        if (cred := await db.get(WebAuthnCredential, key_id)) is None:
            raise PasskeyNotFoundError
        if cred.user_id != user.id:
            raise PasskeyNotFoundError
        if cred.revoked_at is not None:
            raise PasskeyAlreadyRevokedError

        # Count active passkeys; the user-row lock serializes mutations.
        active_count = await db.scalar(
            select(func.count())
            .select_from(WebAuthnCredential)
            .filter(
                WebAuthnCredential.user_id == user.id,
                WebAuthnCredential.revoked_at.is_(None),
            )
        )
        if active_count is not None and int(active_count) <= 1:
            raise LastPasskeyError

        cred.revoked_at = datetime.now(UTC)
        await db.commit()
    except Exception:
        # Roll back so row locks are released promptly.
        await db.rollback()
        raise


async def cleanup_expired_challenges(db: AsyncSession) -> int:
    """Delete expired and consumed challenges. Returns count deleted."""
    from sqlalchemy import delete

    now = datetime.now(UTC)
    result = await db.execute(
        delete(WebAuthnChallenge).filter(WebAuthnChallenge.expires_at < now)
    )
    await db.commit()
    count: int = result.rowcount  # type: ignore[attr-defined]
    return count
