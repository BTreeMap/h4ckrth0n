"""Pydantic schemas for passkey (WebAuthn) endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# -- Registration --


class PasskeyRegisterStartResponse(BaseModel):
    flow_id: str = Field(..., description="Server-generated flow ID for registration.")
    options: dict = Field(
        ...,
        description="PublicKeyCredentialCreationOptions payload as a JSON-safe dict.",
    )


class PasskeyRegisterFinishRequest(BaseModel):
    flow_id: str = Field(..., description="Flow ID returned by register/start.")
    credential: dict = Field(
        ...,
        description="Browser PublicKeyCredential response as JSON.",
    )
    device_public_key_jwk: dict | None = Field(
        None,
        description="Optional device public key in JWK format to bind a device identity.",
    )
    device_label: str | None = Field(None, description="Optional label for the device.")


# -- Authentication --


class PasskeyLoginStartResponse(BaseModel):
    flow_id: str = Field(..., description="Server-generated flow ID for login.")
    options: dict = Field(
        ...,
        description="PublicKeyCredentialRequestOptions payload as a JSON-safe dict.",
    )


class PasskeyLoginFinishRequest(BaseModel):
    flow_id: str = Field(..., description="Flow ID returned by login/start.")
    credential: dict = Field(
        ...,
        description="Browser PublicKeyCredential response as JSON.",
    )
    device_public_key_jwk: dict | None = Field(
        None,
        description="Optional device public key in JWK format to bind a device identity.",
    )
    device_label: str | None = Field(None, description="Optional label for the device.")


# -- Add credential (authenticated) --


class PasskeyAddStartResponse(BaseModel):
    flow_id: str = Field(..., description="Server-generated flow ID for add passkey.")
    options: dict = Field(
        ...,
        description="PublicKeyCredentialCreationOptions payload as a JSON-safe dict.",
    )


class PasskeyAddFinishRequest(BaseModel):
    flow_id: str = Field(..., description="Flow ID returned by add/start.")
    credential: dict = Field(
        ...,
        description="Browser PublicKeyCredential response as JSON.",
    )
    device_public_key_jwk: dict | None = Field(
        None,
        description="Optional device public key in JWK format to bind a device identity.",
    )
    device_label: str | None = Field(None, description="Optional label for the device.")


# -- List / revoke --


class PasskeyInfo(BaseModel):
    id: str = Field(..., description="Internal passkey ID that starts with the k prefix.")
    label: str | None = Field(None, description="Optional passkey nickname.")
    created_at: datetime = Field(..., description="Creation timestamp in UTC.")
    last_used_at: datetime | None = Field(None, description="Last successful use timestamp.")
    revoked_at: datetime | None = Field(None, description="Revocation timestamp, if revoked.")


class PasskeyListResponse(BaseModel):
    passkeys: list[PasskeyInfo] = Field(..., description="Passkeys for the current user.")


class PasskeyRevokeResponse(BaseModel):
    message: str = Field(..., description="Status message for the revocation action.")


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
