"""FastAPI dependencies for endpoint protection."""

from __future__ import annotations

import json
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.algorithms import ECAlgorithm
from sqlalchemy.orm import Session

from h4ckath0n.auth.jwt import (
    JWTClaims,
    decode_access_token,
    decode_device_token,
    get_unverified_kid,
)
from h4ckath0n.auth.models import Device, User

_bearer = HTTPBearer()


def _get_db_from_request(request: Request) -> Session:
    return request.app.state.session_factory()  # type: ignore[no-any-return]


def _get_claims(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> JWTClaims:
    settings = request.app.state.settings
    token = credentials.credentials

    # Try device-key verification first (ES256 with kid)
    kid = get_unverified_kid(token)
    if kid:
        db: Session = _get_db_from_request(request)
        try:
            device = db.query(Device).filter(Device.id == kid).first()
            if device:
                jwk_dict = json.loads(device.public_key_jwk)
                public_key = ECAlgorithm(ECAlgorithm.SHA256).from_jwk(jwk_dict)
                pem = public_key.public_bytes(  # type: ignore[union-attr]
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                ).decode()
                return decode_device_token(token, public_key_pem=pem)
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
            ) from None
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            ) from None
        finally:
            db.close()

    # Fallback: try server-issued HMAC token
    try:
        return decode_access_token(
            token,
            signing_key=settings.effective_signing_key(),
            algorithm=settings.auth_algorithm,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from None


def _get_current_user(
    request: Request,
    claims: JWTClaims = Depends(_get_claims),
) -> User:
    db: Session = _get_db_from_request(request)
    try:
        user = db.query(User).filter(User.id == claims.sub).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    finally:
        db.close()


def require_user() -> Any:
    """Dependency that returns the current authenticated user."""
    return Depends(_get_current_user)


def require_admin() -> Any:
    """Dependency that requires the current user to be an admin."""

    def _admin(user: User = Depends(_get_current_user)) -> User:
        if user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
        return user

    return Depends(_admin)


def require_scopes(*scopes: str) -> Any:
    """Dependency that requires the user's JWT to carry specific scopes."""

    needed: list[str] = list(scopes)

    def _scoped(claims: JWTClaims = Depends(_get_claims)) -> JWTClaims:
        for s in needed:
            if s not in claims.scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing scope: {s}",
                )
        return claims

    return Depends(_scoped)
