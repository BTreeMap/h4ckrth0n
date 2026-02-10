"""Pydantic schemas for passkey (WebAuthn) endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

# -- Registration --


class PasskeyRegisterStartResponse(BaseModel):
    flow_id: str
    options: dict  # PublicKeyCredentialCreationOptions as JSON-safe dict


class PasskeyRegisterFinishRequest(BaseModel):
    flow_id: str
    credential: dict  # browser PublicKeyCredential response as JSON


# -- Authentication --


class PasskeyLoginStartResponse(BaseModel):
    flow_id: str
    options: dict  # PublicKeyCredentialRequestOptions as JSON-safe dict


class PasskeyLoginFinishRequest(BaseModel):
    flow_id: str
    credential: dict  # browser PublicKeyCredential response as JSON


# -- Add credential (authenticated) --


class PasskeyAddStartResponse(BaseModel):
    flow_id: str
    options: dict


class PasskeyAddFinishRequest(BaseModel):
    flow_id: str
    credential: dict


# -- List / revoke --


class PasskeyInfo(BaseModel):
    id: str
    nickname: str | None
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class PasskeyListResponse(BaseModel):
    passkeys: list[PasskeyInfo]


class PasskeyRevokeResponse(BaseModel):
    message: str


class PasskeyRevokeError(BaseModel):
    code: str
    message: str
