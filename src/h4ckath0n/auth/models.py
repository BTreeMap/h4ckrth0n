"""Auth SQLAlchemy models.

The default auth path is passkeys (WebAuthn).  Password-based fields
(``email``, ``password_hash``) are **optional** and only used when the
``h4ckath0n[password]`` extra is installed and explicitly enabled.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Index, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from h4ckath0n.auth.passkeys.ids import new_device_id, new_key_id, new_token_id, new_user_id
from h4ckath0n.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "h4ckath0n_users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_user_id)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    scopes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Optional password fields (only when password extra enabled)
    email: Mapped[str | None] = mapped_column(
        String(320), unique=True, nullable=True, index=True, default=None
    )
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)


# ---------------------------------------------------------------------------
# WebAuthnCredential  (many-to-one with User)
# ---------------------------------------------------------------------------


class WebAuthnCredential(Base):
    __tablename__ = "h4ckath0n_webauthn_credentials"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_key_id)
    user_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    credential_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(nullable=False, default=0)
    aaguid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    transports: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# WebAuthnChallenge  (ceremony state store)
# ---------------------------------------------------------------------------


class WebAuthnChallenge(Base):
    __tablename__ = "h4ckath0n_webauthn_challenges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    challenge: Mapped[str] = mapped_column(Text, nullable=False)  # base64url-encoded
    user_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    kind: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "register" | "authenticate" | "add_credential"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rp_id: Mapped[str] = mapped_column(String(255), nullable=False)
    origin: Mapped[str] = mapped_column(String(512), nullable=False)

    __table_args__ = (Index("ix_h4ckath0n_webauthn_challenges_expires_at", "expires_at"),)


# ---------------------------------------------------------------------------
# PasswordResetToken  (only used with password extra)
# ---------------------------------------------------------------------------


class PasswordResetToken(Base):
    __tablename__ = "h4ckath0n_password_reset_tokens"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_token_id)
    user_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ---------------------------------------------------------------------------
# Device  (stores device public keys for ES256 JWT verification)
# ---------------------------------------------------------------------------


class Device(Base):
    __tablename__ = "h4ckath0n_devices"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_device_id)
    user_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    public_key_jwk: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-serialized JWK
    fingerprint: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )  # SHA-256 hex of canonical JWK
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
