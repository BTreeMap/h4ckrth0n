"""Pydantic schemas for passkey (WebAuthn) endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from h4ckath0n.auth.schemas import (
    DeviceBindingMixin,
    ValidDisplayName,
)


class PasskeyRegisterStartRequest(BaseModel):
    display_name: ValidDisplayName = Field(
        ...,
        description="Human-facing display name for the new account.",
    )


class PasskeyRegisterStartResponse(BaseModel):
    flow_id: str = Field(..., description="Server-generated flow ID for registration.")
    options: dict[str, Any] = Field(
        ...,
        description="PublicKeyCredentialCreationOptions payload as a JSON-safe dict.",
    )


class PasskeyRegisterFinishRequest(DeviceBindingMixin):
    flow_id: str = Field(..., description="Flow ID returned by register/start.")
    credential: dict[str, Any] = Field(
        ...,
        description="Browser PublicKeyCredential response as JSON.",
    )


class PasskeyLoginStartResponse(BaseModel):
    flow_id: str = Field(..., description="Server-generated flow ID for login.")
    options: dict[str, Any] = Field(
        ...,
        description="PublicKeyCredentialRequestOptions payload as a JSON-safe dict.",
    )


class PasskeyLoginFinishRequest(DeviceBindingMixin):
    flow_id: str = Field(..., description="Flow ID returned by login/start.")
    credential: dict[str, Any] = Field(
        ...,
        description="Browser PublicKeyCredential response as JSON.",
    )


class PasskeyAddStartResponse(BaseModel):
    flow_id: str = Field(..., description="Server-generated flow ID for add passkey.")
    options: dict[str, Any] = Field(
        ...,
        description="PublicKeyCredentialCreationOptions payload as a JSON-safe dict.",
    )


class PasskeyAddFinishRequest(DeviceBindingMixin):
    flow_id: str = Field(..., description="Flow ID returned by add/start.")
    credential: dict[str, Any] = Field(
        ...,
        description="Browser PublicKeyCredential response as JSON.",
    )


class PasskeyInfo(BaseModel):
    id: str = Field(
        ..., description="Internal passkey ID that starts with the k prefix."
    )
    name: str | None = Field(None, description="User-provided passkey name.")
    created_at: datetime = Field(..., description="Creation timestamp in UTC.")
    last_used_at: datetime | None = Field(
        None, description="Last successful use timestamp."
    )
    revoked_at: datetime | None = Field(
        None, description="Revocation timestamp, if revoked."
    )


class PasskeyListResponse(BaseModel):
    passkeys: list[PasskeyInfo] = Field(
        ..., description="Passkeys for the current user."
    )


class PasskeyRevokeResponse(BaseModel):
    message: str = Field(..., description="Status message for the revocation action.")


class PasskeyRenameRequest(BaseModel):
    name: str | None = Field(
        None,
        description="New passkey name. Null or empty to clear.",
        max_length=64,
    )


class PasskeyRenameResponse(BaseModel):
    id: str = Field(..., description="Internal passkey ID.")
    name: str | None = Field(None, description="Updated passkey name.")


class PasskeyRevokeError(BaseModel):
    code: str = Field(..., description="Stable error code for the failure.")
    message: str = Field(..., description="Human-readable error message.")


class PasskeyFinishResponse(BaseModel):
    user_id: str = Field(..., description="User ID that starts with the u prefix.")
    device_id: str = Field(
        ...,
        description="Device ID that starts with the d prefix, empty when no device key is bound.",
    )
    role: str = Field(..., description="Server-side role for the user.")
    display_name: str | None = Field(
        None,
        description="Optional display name for the user, not set by default.",
    )
