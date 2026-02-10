"""Auth business logic.

Password-based functions require the ``h4ckath0n[password]`` extra (argon2-cffi).
They will raise ``RuntimeError`` if called without the extra installed.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from h4ckath0n.auth.models import PasswordResetToken, RefreshToken, User
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


def _is_bootstrap_admin(email: str, settings: Settings, db: Session) -> bool:
    """Decide whether a newly-registered user should be admin."""
    if email in settings.bootstrap_admin_emails:
        return True
    if settings.first_user_is_admin:
        count = db.query(User).count()
        if count == 0:
            return True
    return False


def register_user(
    db: Session,
    email: str,
    password: str,
    settings: Settings,
) -> User:
    hash_password, _verify = _require_password_extra()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise ValueError("Email already registered")
    role = "admin" if _is_bootstrap_admin(email, settings, db) else "user"
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    _hash, verify_password = _require_password_extra()
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return None
    if not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_refresh_token(
    db: Session,
    user_id: str,
    expire_days: int = 30,
) -> str:
    """Create and store a refresh token. Returns the raw token string."""
    raw = secrets.token_urlsafe(48)
    rt = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        expires_at=datetime.now(UTC) + timedelta(days=expire_days),
    )
    db.add(rt)
    db.commit()
    return raw


def rotate_refresh_token(
    db: Session,
    raw_token: str,
    expire_days: int = 30,
) -> tuple[str, str]:
    """Validate, revoke, and re-issue a refresh token. Returns (new_raw, user_id)."""
    hashed = _hash_token(raw_token)
    rt = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == hashed,
            RefreshToken.revoked.is_(False),
        )
        .first()
    )
    if rt is None:
        raise ValueError("Invalid refresh token")
    if rt.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise ValueError("Refresh token expired")
    rt.revoked = True
    db.commit()
    new_raw = create_refresh_token(db, rt.user_id, expire_days=expire_days)
    return new_raw, rt.user_id


def revoke_refresh_token(db: Session, raw_token: str) -> None:
    hashed = _hash_token(raw_token)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == hashed).first()
    if rt:
        rt.revoked = True
        db.commit()


def create_password_reset_token(
    db: Session,
    email: str,
    expire_minutes: int = 30,
) -> str | None:
    """Create a password reset token. Returns raw token or None if email unknown."""
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return None
    raw = secrets.token_urlsafe(48)
    prt = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(raw),
        expires_at=datetime.now(UTC) + timedelta(minutes=expire_minutes),
    )
    db.add(prt)
    db.commit()
    return raw


def confirm_password_reset(db: Session, raw_token: str, new_password: str) -> None:
    hash_password, _verify = _require_password_extra()
    hashed = _hash_token(raw_token)
    prt = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == hashed,
            PasswordResetToken.used.is_(False),
        )
        .first()
    )
    if prt is None:
        raise ValueError("Invalid or already-used reset token")
    if prt.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise ValueError("Reset token expired")
    prt.used = True
    user = db.query(User).filter(User.id == prt.user_id).first()
    if user is None:
        raise ValueError("User not found")
    user.password_hash = hash_password(new_password)
    db.commit()
