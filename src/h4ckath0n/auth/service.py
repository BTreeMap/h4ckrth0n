"""Auth business logic.

Password-based functions require the ``h4ckath0n[password]`` extra (argon2-cffi).
They will raise ``RuntimeError`` if called without the extra installed.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from h4ckath0n.auth.models import Device, PasswordResetToken, User
from h4ckath0n.config import Settings
from h4ckath0n.rng import token_urlsafe as _rng_urlsafe


def _hash_token(token: str) -> str:
    """SHA-256 hash a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def _require_password_extra() -> tuple:  # type: ignore[type-arg]
    """Import argon2 password helpers. Raises if extra not installed."""
    try:
        from h4ckath0n.auth.passwords import hash_password, verify_password

        return hash_password, verify_password
    except ImportError as exc:
        raise RuntimeError(
            'Password auth requires the "password" extra: pip install "h4ckath0n[password]"'
        ) from exc


async def _is_bootstrap_admin(email: str, settings: Settings, db: AsyncSession) -> bool:
    """Decide whether a newly-registered user should be admin."""
    if email in settings.bootstrap_admin_emails:
        return True
    if settings.first_user_is_admin:
        # ⚡ Bolt: Use limit(1) instead of count() for O(1) existence check
        first_user_id = await db.scalar(select(User.id).limit(1))
        if first_user_id is None:
            return True
    return False


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    settings: Settings,
    *,
    display_name: str | None = None,
) -> User:
    hash_password, _verify = _require_password_extra()
    # ⚡ Bolt: Use scalar() for ID-only lookup instead of full ORM instantiation
    if await db.scalar(select(User.id).filter(User.email == email).limit(1)):
        raise ValueError("Email already registered")
    role = "admin" if await _is_bootstrap_admin(email, settings, db) else "user"
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        display_name=display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# Dummy Argon2id hash keeps unknown-user verification timing comparable.
_DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$sBe/4XHTiis/Rnh3OmC6MQ"
    "$Ey/bmXGmJQaFatFlEr3d1x8tJEnD2/aghBD9j4nrNmQ"
)


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    _hash, verify_password = _require_password_extra()
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()
    if user is None or not user.password_hash:
        verify_password(password, _DUMMY_PASSWORD_HASH)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def _jwk_fingerprint(jwk: dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 fingerprint of a JWK.

    Uses only the essential key-material fields (kty, crv, x, y) in sorted
    order so the fingerprint is stable regardless of extra metadata the
    client might include.

    Raises :class:`ValueError` when required fields are missing.
    """
    required = ("crv", "kty", "x", "y")
    if missing := [k for k in required if k not in jwk]:
        raise ValueError(f"JWK missing required fields: {', '.join(missing)}")
    canonical = {k: jwk[k] for k in required}
    raw = json.dumps(canonical, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


async def register_device(
    db: AsyncSession,
    user_id: str,
    public_key_jwk: dict[str, Any] | None,
    label: str | None = None,
) -> str:
    """Return a Device id for the given public key, creating one if needed.

    If a device with the same JWK fingerprint already exists the existing
    ``device_id`` is returned (stable identity).  A new record is only
    created when the fingerprint has never been seen before.
    """
    if not public_key_jwk:
        return ""
    fp = _jwk_fingerprint(public_key_jwk)

    # Fetch only ID; avoid instantiating the Device ORM object.
    if existing_id := await db.scalar(
        select(Device.id).filter(Device.fingerprint == fp)
    ):
        return existing_id

    device = Device(
        user_id=user_id,
        public_key_jwk=json.dumps(public_key_jwk),
        fingerprint=fp,
        label=label,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device.id


async def create_password_reset_token(
    db: AsyncSession,
    email: str,
    expire_minutes: int = 30,
) -> str | None:
    """Create a password reset token. Returns raw token or None if email unknown."""
    # Fetch only ID; avoid instantiating the User ORM object.
    if (
        user_id := await db.scalar(select(User.id).filter(User.email == email))
    ) is None:
        return None
    # 32-byte unguessable token; hash before storage.
    raw = _rng_urlsafe(32)
    prt = PasswordResetToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        expires_at=datetime.now(UTC) + timedelta(minutes=expire_minutes),
    )
    db.add(prt)
    await db.commit()
    return raw


async def confirm_password_reset(
    db: AsyncSession, raw_token: str, new_password: str
) -> User:
    """Confirm a password reset and return the user."""
    hash_password, _verify = _require_password_extra()
    hashed = _hash_token(raw_token)
    prt_result = await db.execute(
        select(PasswordResetToken).filter(
            PasswordResetToken.token_hash == hashed,
            PasswordResetToken.used.is_(False),
        )
    )
    if (prt := prt_result.scalars().first()) is None:
        raise ValueError("Invalid or already-used reset token")
    if prt.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise ValueError("Reset token expired")
    prt.used = True
    # Use db.get() for primary key lookup.
    if (user := await db.get(User, prt.user_id)) is None:
        raise ValueError("User not found")
    user.password_hash = hash_password(new_password)
    await db.commit()
    return user
