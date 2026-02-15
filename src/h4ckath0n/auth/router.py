"""Auth API router – mounted at ``/auth``.

Password-based routes (register/login/password-reset) are **only** included
when the ``h4ckath0n[password]`` extra is installed AND
``H4CKATH0N_PASSWORD_AUTH_ENABLED=true``.

Password endpoints authenticate the user's identity and bind a device key.
They do **not** return access/refresh tokens.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from h4ckath0n.auth import schemas
from h4ckath0n.auth.service import (
    authenticate_user,
    confirm_password_reset,
    create_password_reset_token,
    register_device,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _db_dep(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with request.app.state.async_session_factory() as db:
        yield db


# ---------------------------------------------------------------------------
# Password-based routes (optional extra)
# ---------------------------------------------------------------------------


def _password_router() -> APIRouter:
    """Build the password auth sub-router. Only called when password extra is enabled."""
    pw = APIRouter(tags=["password-auth"])

    @pw.post(
        "/register",
        response_model=schemas.DeviceBindingResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Register with password",
        description=(
            "Create a new account using email and password, then bind an optional device key."
        ),
        responses={
            409: {
                "model": schemas.ErrorResponse,
                "description": "Email already registered.",
            }
        },
    )
    async def register(
        body: schemas.RegisterRequest, request: Request, db: AsyncSession = Depends(_db_dep)
    ):
        settings = request.app.state.settings
        try:
            user = await register_user(db, body.email, body.password, settings)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
        device_id = await register_device(
            db, user.id, body.device_public_key_jwk, body.device_label
        )
        return schemas.DeviceBindingResponse(user_id=user.id, device_id=device_id, role=user.role)

    @pw.post(
        "/login",
        response_model=schemas.DeviceBindingResponse,
        summary="Login with password",
        description="Verify email and password, then bind an optional device key.",
        responses={
            401: {
                "model": schemas.ErrorResponse,
                "description": "Invalid email or password.",
            }
        },
    )
    async def login(
        body: schemas.LoginRequest, request: Request, db: AsyncSession = Depends(_db_dep)
    ):
        user = await authenticate_user(db, body.email, body.password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        device_id = await register_device(
            db, user.id, body.device_public_key_jwk, body.device_label
        )
        return schemas.DeviceBindingResponse(user_id=user.id, device_id=device_id, role=user.role)

    @pw.post(
        "/password-reset/request",
        response_model=schemas.MessageResponse,
        summary="Request a password reset",
        description=(
            "Request a password reset token for the account. Returns the same message "
            "even when the email is unknown."
        ),
    )
    async def password_reset_request(
        body: schemas.PasswordResetRequestSchema,
        request: Request,
        db: AsyncSession = Depends(_db_dep),
    ):
        settings = request.app.state.settings
        await create_password_reset_token(
            db, body.email, expire_minutes=settings.password_reset_expire_minutes
        )
        return schemas.MessageResponse(
            message="If that email is registered, a reset link was sent."
        )

    @pw.post(
        "/password-reset/confirm",
        response_model=schemas.DeviceBindingResponse,
        summary="Confirm password reset",
        description=(
            "Confirm a password reset token, set a new password, and bind an optional device key."
        ),
        responses={
            400: {
                "model": schemas.ErrorResponse,
                "description": "Invalid or expired reset token.",
            }
        },
    )
    async def password_reset_confirm(
        body: schemas.PasswordResetConfirmSchema,
        db: AsyncSession = Depends(_db_dep),
    ):
        try:
            user = await confirm_password_reset(db, body.token, body.new_password)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
        device_id = await register_device(
            db, user.id, body.device_public_key_jwk, body.device_label
        )
        return schemas.DeviceBindingResponse(user_id=user.id, device_id=device_id, role=user.role)

    return pw


def get_password_router() -> APIRouter:
    """Return the password sub-router, intended to be included in the main auth router."""
    return _password_router()
