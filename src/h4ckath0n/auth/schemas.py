"""Pydantic schemas for auth endpoints."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Account email for password-based signup.")
    password: str = Field(..., description="Plaintext password, hashed server-side.")
    device_public_key_jwk: dict | None = Field(
        None,
        description="Optional device public key in JWK format to bind a device identity.",
    )
    device_label: str | None = Field(None, description="Optional label for the device.")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Account email for password-based login.")
    password: str = Field(..., description="Plaintext password to verify.")
    device_public_key_jwk: dict | None = Field(
        None,
        description="Optional device public key in JWK format to bind a device identity.",
    )
    device_label: str | None = Field(None, description="Optional label for the device.")


class DeviceBindingResponse(BaseModel):
    user_id: str = Field(..., description="User ID that starts with the u prefix.")
    device_id: str = Field(
        ...,
        description="Device ID that starts with the d prefix, empty when no device key is bound.",
    )
    role: str = Field(..., description="Server-side role for the user.")


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr = Field(..., description="Account email to send a reset token.")


class PasswordResetConfirmSchema(BaseModel):
    token: str = Field(..., description="Password reset token issued by the server.")
    new_password: str = Field(..., description="New password to set for the account.")
    device_public_key_jwk: dict | None = Field(
        None,
        description="Optional device public key in JWK format to bind a device identity.",
    )
    device_label: str | None = Field(None, description="Optional label for the device.")


class MessageResponse(BaseModel):
    message: str = Field(..., description="Human-readable response message.")


class ErrorResponse(BaseModel):
    """Standard error envelope for auth routes."""

    detail: str | dict[str, str] = Field(
        ...,
        description="Error detail message or structured error payload.",
    )
