"""JWT helpers for device-key (ES256) and server (HS256) tokens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pydantic import BaseModel


class JWTClaims(BaseModel):
    """Typed representation of JWT payload."""

    sub: str
    iat: datetime
    exp: datetime
    aud: str | None = None
    iss: str | None = None
    # Server-issued tokens may include role/scopes; device tokens do not.
    role: str = "user"
    scopes: list[str] = []


def create_access_token(
    *,
    user_id: str,
    role: str,
    scopes: list[str],
    signing_key: str,
    algorithm: str = "HS256",
    expire_minutes: int = 15,
) -> str:
    """Create a server-issued HMAC access token (used internally/tests)."""
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "scopes": scopes,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
    }
    return jwt.encode(claims, signing_key, algorithm=algorithm)


def decode_access_token(
    token: str,
    *,
    signing_key: str,
    algorithm: str = "HS256",
) -> JWTClaims:
    """Decode a server-issued HMAC token."""
    payload = jwt.decode(token, signing_key, algorithms=[algorithm])
    return JWTClaims(**payload)


def decode_device_token(
    token: str,
    *,
    public_key_pem: str,
) -> JWTClaims:
    """Decode an ES256 device-signed JWT using the device's public key."""
    payload = jwt.decode(
        token,
        public_key_pem,
        algorithms=["ES256"],
        options={"verify_aud": False},
    )
    return JWTClaims(**payload)


def get_unverified_kid(token: str) -> str | None:
    """Extract the kid from the JWT header without verification."""
    try:
        header = jwt.get_unverified_header(token)
        return header.get("kid")
    except jwt.InvalidTokenError:
        return None
