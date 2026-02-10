"""JWT encode / decode helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pydantic import BaseModel


class JWTClaims(BaseModel):
    """Typed representation of our JWT payload."""

    sub: str
    role: str
    scopes: list[str]
    iat: datetime
    exp: datetime
    aud: str | None = None
    iss: str | None = None


def create_access_token(
    *,
    user_id: str,
    role: str,
    scopes: list[str],
    signing_key: str,
    algorithm: str = "HS256",
    expire_minutes: int = 15,
) -> str:
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
    payload = jwt.decode(token, signing_key, algorithms=[algorithm])
    return JWTClaims(**payload)
