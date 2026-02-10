"""FastAPI dependencies for endpoint protection."""

from __future__ import annotations

from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from h4ckath0n.auth.jwt import JWTClaims, decode_access_token
from h4ckath0n.auth.models import User

_bearer = HTTPBearer()


def _get_db_from_request(request: Request) -> Session:
    return request.app.state.session_factory()  # type: ignore[no-any-return]


def _get_claims(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> JWTClaims:
    settings = request.app.state.settings
    try:
        return decode_access_token(
            credentials.credentials,
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
