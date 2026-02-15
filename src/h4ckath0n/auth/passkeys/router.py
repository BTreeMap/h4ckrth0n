"""Passkey (WebAuthn) API router – mounted at ``/auth/passkey`` by default."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from h4ckath0n.auth import schemas as auth_schemas
from h4ckath0n.auth.dependencies import _get_current_user
from h4ckath0n.auth.models import User
from h4ckath0n.auth.passkeys import schemas
from h4ckath0n.auth.passkeys.service import (
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
from h4ckath0n.auth.service import register_device

router = APIRouter(prefix="/auth/passkey", tags=["passkey"])


# ---------------------------------------------------------------------------
# DB dependency (async)
# ---------------------------------------------------------------------------


async def _db_dep(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with request.app.state.async_session_factory() as db:
        yield db


# ---------------------------------------------------------------------------
# Registration  (unauthenticated)
# ---------------------------------------------------------------------------


@router.post(
    "/register/start",
    response_model=schemas.PasskeyRegisterStartResponse,
    summary="Start passkey registration",
    description=(
        "Begin a passkey registration ceremony. Creates a new user and a single-use "
        "challenge flow, then returns WebAuthn registration options."
    ),
    responses={
        400: {
            "model": auth_schemas.ErrorResponse,
            "description": "Invalid request or WebAuthn configuration error.",
        }
    },
)
async def register_start(request: Request, db: AsyncSession = Depends(_db_dep)):
    settings = request.app.state.settings
    flow_id, options = await start_registration(db, settings)
    return schemas.PasskeyRegisterStartResponse(flow_id=flow_id, options=options)


@router.post(
    "/register/finish",
    response_model=schemas.PasskeyFinishResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Finish passkey registration",
    description=(
        "Finish passkey registration by verifying the WebAuthn attestation for the "
        "flow and binding an optional device key."
    ),
    responses={
        400: {
            "model": auth_schemas.ErrorResponse,
            "description": "Invalid or expired flow, or invalid WebAuthn payload.",
        }
    },
)
async def register_finish(
    body: schemas.PasskeyRegisterFinishRequest,
    request: Request,
    db: AsyncSession = Depends(_db_dep),
):
    settings = request.app.state.settings
    try:
        user = await finish_registration(db, body.flow_id, body.credential, settings)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None

    device_id = await register_device(db, user.id, body.device_public_key_jwk, body.device_label)

    return schemas.PasskeyFinishResponse(user_id=user.id, device_id=device_id, role=user.role)


# ---------------------------------------------------------------------------
# Authentication  (unauthenticated, username-less)
# ---------------------------------------------------------------------------


@router.post(
    "/login/start",
    response_model=schemas.PasskeyLoginStartResponse,
    summary="Start passkey login",
    description=(
        "Begin a username-less passkey login ceremony and return WebAuthn authentication options."
    ),
)
async def login_start(request: Request, db: AsyncSession = Depends(_db_dep)):
    settings = request.app.state.settings
    flow_id, options = await start_authentication(db, settings)
    return schemas.PasskeyLoginStartResponse(flow_id=flow_id, options=options)


@router.post(
    "/login/finish",
    response_model=schemas.PasskeyFinishResponse,
    summary="Finish passkey login",
    description=(
        "Finish passkey login by verifying the WebAuthn assertion for the flow and "
        "binding an optional device key."
    ),
    responses={
        401: {
            "model": auth_schemas.ErrorResponse,
            "description": "Invalid credentials, revoked passkey, or expired flow.",
        }
    },
)
async def login_finish(
    body: schemas.PasskeyLoginFinishRequest,
    request: Request,
    db: AsyncSession = Depends(_db_dep),
):
    settings = request.app.state.settings
    try:
        user = await finish_authentication(db, body.flow_id, body.credential, settings)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from None

    device_id = await register_device(db, user.id, body.device_public_key_jwk, body.device_label)

    return schemas.PasskeyFinishResponse(user_id=user.id, device_id=device_id, role=user.role)


# ---------------------------------------------------------------------------
# Add credential  (authenticated)
# ---------------------------------------------------------------------------


@router.post(
    "/add/start",
    response_model=schemas.PasskeyAddStartResponse,
    summary="Start adding a passkey",
    description=(
        "Begin adding a new passkey for the authenticated user and return registration options."
    ),
    responses={
        401: {"model": auth_schemas.ErrorResponse, "description": "Missing or invalid token."}
    },
)
async def add_start(
    request: Request,
    user: User = Depends(_get_current_user),
    db: AsyncSession = Depends(_db_dep),
):
    settings = request.app.state.settings
    flow_id, options = await start_add_credential(db, user, settings)
    return schemas.PasskeyAddStartResponse(flow_id=flow_id, options=options)


@router.post(
    "/add/finish",
    response_model=schemas.PasskeyFinishResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Finish adding a passkey",
    description="Verify the WebAuthn attestation and attach the new passkey to the user.",
    responses={
        400: {
            "model": auth_schemas.ErrorResponse,
            "description": "Invalid or expired flow, or WebAuthn verification error.",
        },
        401: {"model": auth_schemas.ErrorResponse, "description": "Missing or invalid token."},
    },
)
async def add_finish(
    body: schemas.PasskeyAddFinishRequest,
    request: Request,
    user: User = Depends(_get_current_user),
    db: AsyncSession = Depends(_db_dep),
):
    settings = request.app.state.settings
    try:
        await finish_add_credential(db, body.flow_id, body.credential, user, settings)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None

    device_id = await register_device(db, user.id, body.device_public_key_jwk, body.device_label)

    return schemas.PasskeyFinishResponse(user_id=user.id, device_id=device_id, role=user.role)


# ---------------------------------------------------------------------------
# List / Revoke  (authenticated, mounted at /auth/passkeys)
# ---------------------------------------------------------------------------

passkeys_router = APIRouter(prefix="/auth/passkeys", tags=["passkey"])


@passkeys_router.get(
    "",
    response_model=schemas.PasskeyListResponse,
    summary="List passkeys",
    description="List all passkeys, including revoked entries, for the current user.",
    responses={
        401: {"model": auth_schemas.ErrorResponse, "description": "Missing or invalid token."}
    },
)
async def passkeys_list(
    request: Request,
    user: User = Depends(_get_current_user),
    db: AsyncSession = Depends(_db_dep),
):
    creds = await list_passkeys(db, user)
    items = [
        schemas.PasskeyInfo(
            id=c.id,
            label=c.nickname,
            created_at=c.created_at,
            last_used_at=c.last_used_at,
            revoked_at=c.revoked_at,
        )
        for c in creds
    ]
    return schemas.PasskeyListResponse(passkeys=items)


@passkeys_router.post(
    "/{key_id}/revoke",
    response_model=schemas.PasskeyRevokeResponse,
    summary="Revoke a passkey",
    description=(
        "Revoke a passkey by its internal key ID. The last active passkey cannot be revoked "
        "and returns the LAST_PASSKEY error."
    ),
    responses={
        401: {"model": auth_schemas.ErrorResponse, "description": "Missing or invalid token."},
        404: {"model": auth_schemas.ErrorResponse, "description": "Passkey not found."},
        409: {
            "model": auth_schemas.ErrorResponse,
            "description": "Cannot revoke the last active passkey.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "LAST_PASSKEY",
                            "message": "Cannot revoke the last active passkey.",
                        }
                    }
                }
            },
        },
    },
)
async def passkey_revoke(
    key_id: str,
    request: Request,
    user: User = Depends(_get_current_user),
    db: AsyncSession = Depends(_db_dep),
):
    try:
        await revoke_passkey(db, user, key_id)
    except LastPasskeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=schemas.PasskeyRevokeError(
                code="LAST_PASSKEY",
                message=(
                    "Cannot revoke the last active passkey. Add another passkey via "
                    "POST /auth/passkey/add/start first."
                ),
            ).model_dump(),
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None
    return schemas.PasskeyRevokeResponse(message="Passkey revoked")
