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
    device_public_key_jwk: dict | None = None
    device_label: str | None = None


# -- Authentication --


class PasskeyLoginStartResponse(BaseModel):
    flow_id: str
    options: dict  # PublicKeyCredentialRequestOptions as JSON-safe dict


class PasskeyLoginFinishRequest(BaseModel):
    flow_id: str
    credential: dict  # browser PublicKeyCredential response as JSON
    device_public_key_jwk: dict | None = None
    device_label: str | None = None


# -- Add credential (authenticated) --


class PasskeyAddStartResponse(BaseModel):
    flow_id: str
    options: dict


class PasskeyAddFinishRequest(BaseModel):
    flow_id: str
    credential: dict
    device_public_key_jwk: dict | None = None
    device_label: str | None = None


# -- List / revoke --


class PasskeyInfo(BaseModel):
    id: str
    label: str | None
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


class PasskeyFinishResponse(BaseModel):
    user_id: str
    device_id: str
    role: str
    display_name: str | None = None
