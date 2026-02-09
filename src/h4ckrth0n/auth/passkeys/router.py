"""Passkey (WebAuthn) API router – mounted at ``/auth/passkey`` by default."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from h4ckrth0n.auth.dependencies import _get_current_user
from h4ckrth0n.auth.jwt import create_access_token
from h4ckrth0n.auth.models import User
from h4ckrth0n.auth.passkeys import schemas
from h4ckrth0n.auth.passkeys.service import (
    LastPasskeyError,
    finish_add_credential,
    finish_authentication,
    finish_registration,
    list_passkeys,
    revoke_passkey,
    start_add_credential,
    start_authentication,
    start_registration,
)
from h4ckrth0n.auth.service import create_refresh_token

router = APIRouter(prefix="/auth/passkey", tags=["passkey"])


# ---------------------------------------------------------------------------
# DB dependency (same pattern as main auth router)
# ---------------------------------------------------------------------------


def _db_dep(request: Request):  # type: ignore[no-untyped-def]
    db: Session = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()


def _tokens(user: User, request: Request, db: Session) -> dict:
    """Issue access + refresh tokens for *user*."""
    settings = request.app.state.settings
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
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# Registration  (unauthenticated)
# ---------------------------------------------------------------------------


@router.post("/register/start", response_model=schemas.PasskeyRegisterStartResponse)
def register_start(request: Request, db: Session = Depends(_db_dep)):
    settings = request.app.state.settings
    flow_id, options = start_registration(db, settings)
    return schemas.PasskeyRegisterStartResponse(flow_id=flow_id, options=options)


@router.post("/register/finish", status_code=status.HTTP_201_CREATED)
def register_finish(
    body: schemas.PasskeyRegisterFinishRequest,
    request: Request,
    db: Session = Depends(_db_dep),
):
    settings = request.app.state.settings
    try:
        user = finish_registration(db, body.flow_id, body.credential, settings)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    return _tokens(user, request, db)


# ---------------------------------------------------------------------------
# Authentication  (unauthenticated, username-less)
# ---------------------------------------------------------------------------


@router.post("/login/start", response_model=schemas.PasskeyLoginStartResponse)
def login_start(request: Request, db: Session = Depends(_db_dep)):
    settings = request.app.state.settings
    flow_id, options = start_authentication(db, settings)
    return schemas.PasskeyLoginStartResponse(flow_id=flow_id, options=options)


@router.post("/login/finish")
def login_finish(
    body: schemas.PasskeyLoginFinishRequest,
    request: Request,
    db: Session = Depends(_db_dep),
):
    settings = request.app.state.settings
    try:
        user = finish_authentication(db, body.flow_id, body.credential, settings)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from None
    return _tokens(user, request, db)


# ---------------------------------------------------------------------------
# Add credential  (authenticated)
# ---------------------------------------------------------------------------


@router.post("/add/start", response_model=schemas.PasskeyAddStartResponse)
def add_start(
    request: Request,
    user: User = Depends(_get_current_user),
    db: Session = Depends(_db_dep),
):
    settings = request.app.state.settings
    flow_id, options = start_add_credential(db, user, settings)
    return schemas.PasskeyAddStartResponse(flow_id=flow_id, options=options)


@router.post("/add/finish", status_code=status.HTTP_201_CREATED)
def add_finish(
    body: schemas.PasskeyAddFinishRequest,
    request: Request,
    user: User = Depends(_get_current_user),
    db: Session = Depends(_db_dep),
):
    settings = request.app.state.settings
    try:
        cred = finish_add_credential(db, body.flow_id, body.credential, user, settings)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    return {"id": cred.id, "created_at": cred.created_at.isoformat()}


# ---------------------------------------------------------------------------
# List / Revoke  (authenticated, mounted at /auth/passkeys)
# ---------------------------------------------------------------------------

passkeys_router = APIRouter(prefix="/auth/passkeys", tags=["passkey"])


@passkeys_router.get("", response_model=schemas.PasskeyListResponse)
def passkeys_list(
    request: Request,
    user: User = Depends(_get_current_user),
    db: Session = Depends(_db_dep),
):
    creds = list_passkeys(db, user)
    items = [
        schemas.PasskeyInfo(
            id=c.id,
            nickname=c.nickname,
            created_at=c.created_at,
            last_used_at=c.last_used_at,
            revoked_at=c.revoked_at,
        )
        for c in creds
    ]
    return schemas.PasskeyListResponse(passkeys=items)


@passkeys_router.post("/{key_id}/revoke")
def passkey_revoke(
    key_id: str,
    request: Request,
    user: User = Depends(_get_current_user),
    db: Session = Depends(_db_dep),
):
    try:
        revoke_passkey(db, user, key_id)
    except LastPasskeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "LAST_PASSKEY",
                "message": "Cannot revoke the last active passkey. "
                "Add another passkey via POST /auth/passkey/add/start first.",
            },
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None
    return schemas.PasskeyRevokeResponse(message="Passkey revoked")
