"""Auth business logic.

Password-based functions require the ``h4ckath0n[password]`` extra (argon2-cffi).
They will raise ``RuntimeError`` if called without the extra installed.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from h4ckath0n.auth.models import Device, PasswordResetToken, User
from h4ckath0n.config import Settings


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
        result = await db.execute(select(func.count()).select_from(User))
        count = result.scalar()
        if count == 0:
            return True
    return False


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    settings: Settings,
) -> User:
    hash_password, _verify = _require_password_extra()
    result = await db.execute(select(User).filter(User.email == email))
    existing = result.scalars().first()
    if existing:
        raise ValueError("Email already registered")
    role = "admin" if await _is_bootstrap_admin(email, settings, db) else "user"
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    _hash, verify_password = _require_password_extra()
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()
    if user is None:
        return None
    if not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def _jwk_fingerprint(jwk: dict) -> str:
    """Compute a deterministic SHA-256 fingerprint of a JWK.

    Uses only the essential key-material fields (kty, crv, x, y) in sorted
    order so the fingerprint is stable regardless of extra metadata the
    client might include.

    Raises :class:`ValueError` when required fields are missing.
    """
    required = ("crv", "kty", "x", "y")
    missing = [k for k in required if k not in jwk]
    if missing:
        raise ValueError(f"JWK missing required fields: {', '.join(missing)}")
    canonical = {k: jwk[k] for k in required}
    raw = json.dumps(canonical, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


async def register_device(
    db: AsyncSession,
    user_id: str,
    public_key_jwk: dict | None,
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

    result = await db.execute(select(Device).filter(Device.fingerprint == fp))
    existing = result.scalars().first()
    if existing:
        return existing.id

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
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()
    if user is None:
        return None
    raw = secrets.token_urlsafe(48)
    prt = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(raw),
        expires_at=datetime.now(UTC) + timedelta(minutes=expire_minutes),
    )
    db.add(prt)
    await db.commit()
    return raw


async def confirm_password_reset(db: AsyncSession, raw_token: str, new_password: str) -> User:
    """Confirm a password reset and return the user."""
    hash_password, _verify = _require_password_extra()
    hashed = _hash_token(raw_token)
    prt_result = await db.execute(
        select(PasswordResetToken).filter(
            PasswordResetToken.token_hash == hashed,
            PasswordResetToken.used.is_(False),
        )
    )
    prt = prt_result.scalars().first()
    if prt is None:
        raise ValueError("Invalid or already-used reset token")
    if prt.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise ValueError("Reset token expired")
    prt.used = True
    user_result = await db.execute(select(User).filter(User.id == prt.user_id))
    user = user_result.scalars().first()
    if user is None:
        raise ValueError("User not found")
    user.password_hash = hash_password(new_password)
    await db.commit()
    return user
