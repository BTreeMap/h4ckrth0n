"""Pydantic schemas for auth endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, EmailStr, Field

# Maximum length for display names (shared across DB, schemas, and API).
DISPLAY_NAME_MAX_LENGTH = 200


def normalize_display_name(value: str) -> str:
    """Trim a required display name and reject an empty value."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Display name must not be empty")
    return cleaned


# Reusable, self-validating type for display names.
DisplayName = Annotated[
    str,
    Field(max_length=DISPLAY_NAME_MAX_LENGTH),
    AfterValidator(normalize_display_name),
]


class DeviceBindingMixin(BaseModel):
    device_public_key_jwk: dict[str, Any] | None = Field(
        None,
        description="Optional device public key in JWK format to bind a device identity.",
    )
    device_label: str | None = Field(None, description="Optional label for the device.")


class RegisterRequest(DeviceBindingMixin):
    email: EmailStr = Field(..., description="Account email for password-based signup.")
    password: str = Field(..., description="Plaintext password, hashed server-side.")
    display_name: DisplayName = Field(
        ...,
        description="Human-facing display name for the account.",
    )


class LoginRequest(DeviceBindingMixin):
    email: EmailStr = Field(..., description="Account email for password-based login.")
    password: str = Field(..., description="Plaintext password to verify.")


class DeviceBindingResponse(BaseModel):
    user_id: str = Field(..., description="User ID that starts with the u prefix.")
    device_id: str = Field(
        ...,
        description="Device ID that starts with the d prefix, empty when no device key is bound.",
    )
    role: str = Field(..., description="Server-side role for the user.")
    display_name: str | None = Field(
        None,
        description="Human-facing display name for the user.",
    )


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr = Field(..., description="Account email to send a reset token.")


class PasswordResetConfirmSchema(DeviceBindingMixin):
    token: str = Field(..., description="Password reset token issued by the server.")
    new_password: str = Field(..., description="New password to set for the account.")


class MessageResponse(BaseModel):
    message: str = Field(..., description="Human-readable response message.")


class SessionResponse(BaseModel):
    """Current authenticated session info."""

    user_id: str = Field(..., description="User ID.")
    device_id: str = Field(..., description="Device ID from the verified JWT.")
    role: str = Field(..., description="Server-side role.")
    scopes: list[str] = Field(..., description="User scopes as a list.")
    display_name: str | None = Field(None, description="Display name.")
    email: str | None = Field(None, description="User email if set.")


class ErrorResponse(BaseModel):
    """Standard error envelope for auth routes."""

    detail: str | dict[str, str] = Field(
        ...,
        description="Error detail message or structured error payload.",
    )
