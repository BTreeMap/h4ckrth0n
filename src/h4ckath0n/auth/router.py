"""Auth API router – mounted at ``/auth``.

Password-based routes (register/login/password-reset) are **only** included
when the ``h4ckath0n[password]`` extra is installed AND
``H4CKATH0N_PASSWORD_AUTH_ENABLED=true``.

The passkey router is always available (see ``passkeys/router.py``).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from h4ckath0n.auth import schemas
from h4ckath0n.auth.jwt import create_access_token
from h4ckath0n.auth.models import User
from h4ckath0n.auth.service import (
    authenticate_user,
    confirm_password_reset,
    create_password_reset_token,
    create_refresh_token,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _db_dep(request: Request):  # type: ignore[no-untyped-def]
    db: Session = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Token management (always available)
# ---------------------------------------------------------------------------


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh(body: schemas.RefreshRequest, request: Request, db: Session = Depends(_db_dep)):
    settings = request.app.state.settings
    try:
        new_raw, user_id = rotate_refresh_token(
            db, body.refresh_token, expire_days=settings.refresh_token_expire_days
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from None
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    scopes = [s for s in user.scopes.split(",") if s]
    access = create_access_token(
        user_id=user.id,
        role=user.role,
        scopes=scopes,
        signing_key=settings.effective_signing_key(),
        algorithm=settings.auth_algorithm,
        expire_minutes=settings.access_token_expire_minutes,
    )
    return schemas.TokenResponse(access_token=access, refresh_token=new_raw)


@router.post("/logout", response_model=schemas.MessageResponse)
def logout(body: schemas.LogoutRequest, db: Session = Depends(_db_dep)):
    revoke_refresh_token(db, body.refresh_token)
    return schemas.MessageResponse(message="Logged out")


# ---------------------------------------------------------------------------
# Password-based routes (optional extra)
# ---------------------------------------------------------------------------


def _password_router() -> APIRouter:
    """Build the password auth sub-router. Only called when password extra is enabled."""
    pw = APIRouter(tags=["password-auth"])

    @pw.post(
        "/register", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED
    )
    def register(body: schemas.RegisterRequest, request: Request, db: Session = Depends(_db_dep)):
        settings = request.app.state.settings
        try:
            user = register_user(db, body.email, body.password, settings)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
        scopes = [s for s in user.scopes.split(",") if s]
        access = create_access_token(
            user_id=user.id,
            role=user.role,
            scopes=scopes,
            signing_key=settings.effective_signing_key(),
            algorithm=settings.auth_algorithm,
            expire_minutes=settings.access_token_expire_minutes,
        )
        refresh = create_refresh_token(db, user.id, expire_days=settings.refresh_token_expire_days)
        return schemas.TokenResponse(access_token=access, refresh_token=refresh)

    @pw.post("/login", response_model=schemas.TokenResponse)
    def login(body: schemas.LoginRequest, request: Request, db: Session = Depends(_db_dep)):
        settings = request.app.state.settings
        user = authenticate_user(db, body.email, body.password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        scopes = [s for s in user.scopes.split(",") if s]
        access = create_access_token(
            user_id=user.id,
            role=user.role,
            scopes=scopes,
            signing_key=settings.effective_signing_key(),
            algorithm=settings.auth_algorithm,
            expire_minutes=settings.access_token_expire_minutes,
        )
        refresh = create_refresh_token(db, user.id, expire_days=settings.refresh_token_expire_days)
        return schemas.TokenResponse(access_token=access, refresh_token=refresh)

    @pw.post("/password-reset/request", response_model=schemas.MessageResponse)
    def password_reset_request(
        body: schemas.PasswordResetRequestSchema,
        request: Request,
        db: Session = Depends(_db_dep),
    ):
        settings = request.app.state.settings
        create_password_reset_token(
            db, body.email, expire_minutes=settings.password_reset_expire_minutes
        )
        return schemas.MessageResponse(
            message="If that email is registered, a reset link was sent."
        )

    @pw.post("/password-reset/confirm", response_model=schemas.MessageResponse)
    def password_reset_confirm(
        body: schemas.PasswordResetConfirmSchema,
        db: Session = Depends(_db_dep),
    ):
        try:
            confirm_password_reset(db, body.token, body.new_password)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
        return schemas.MessageResponse(message="Password has been reset.")

    return pw


def get_password_router() -> APIRouter:
    """Return the password sub-router, intended to be included in the main auth router."""
    return _password_router()
