"""FastAPI dependencies for endpoint protection.

All request authentication uses device-signed ES256 JWTs.  Authorization
(roles, scopes) is loaded from the database – the JWT carries no privilege
claims.

The core verification logic lives in :mod:`h4ckath0n.realtime.auth` so
that HTTP, WebSocket and SSE endpoints all share a single code path.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from h4ckath0n.auth.models import User
from h4ckath0n.realtime.auth import AUD_HTTP, AuthContext, AuthError, verify_device_jwt

_bearer = HTTPBearer(
    scheme_name="DeviceJWT",
    description=(
        "Device-signed ES256 JWT minted by the client. The JWT header must include "
        "kid set to the device id, and the aud claim must be h4ckath0n:http."
    ),
)


async def _get_async_db_from_request(request: Request) -> AsyncSession:
    return request.app.state.async_session_factory()  # type: ignore[no-any-return]


async def _get_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> AuthContext:
    token = credentials.credentials
    db: AsyncSession = await _get_async_db_from_request(request)
    try:
        return await verify_device_jwt(token, expected_aud=AUD_HTTP, db=db)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.detail,
        ) from None
    finally:
        await db.close()


async def _get_current_user(
    request: Request,
    ctx: AuthContext = Depends(_get_auth_context),
) -> User:
    db: AsyncSession = await _get_async_db_from_request(request)
    try:
        result = await db.execute(select(User).filter(User.id == ctx.user_id))
        user = result.scalars().first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    finally:
        await db.close()


def require_user() -> Any:
    """Dependency that returns the current authenticated user."""
    return Depends(_get_current_user)


def require_admin() -> Any:
    """Dependency that requires the current user to be an admin."""

    async def _admin(user: User = Depends(_get_current_user)) -> User:
        if user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
        return user

    return Depends(_admin)


def require_scopes(*scopes: str) -> Any:
    """Dependency that requires the user to have specific scopes (from DB)."""

    needed: list[str] = list(scopes)

    async def _scoped(user: User = Depends(_get_current_user)) -> User:
        user_scopes = [s for s in user.scopes.split(",") if s]
        for s in needed:
            if s not in user_scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing scope: {s}",
                )
        return user

    return Depends(_scoped)
