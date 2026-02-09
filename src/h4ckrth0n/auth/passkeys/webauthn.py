"""Thin wrapper around py_webauthn for option construction and verification."""

from __future__ import annotations

import json
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Any

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import (
    parse_authentication_credential_json,
    parse_registration_credential_json,
)
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from h4ckrth0n.config import Settings


def _uv(settings: Settings) -> UserVerificationRequirement:
    """Map setting string to webauthn enum value."""
    return UserVerificationRequirement(settings.user_verification)


def _att(settings: Settings) -> AttestationConveyancePreference:
    return AttestationConveyancePreference(settings.attestation)


def bytes_to_base64url(b: bytes) -> str:
    return urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def base64url_to_bytes(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return urlsafe_b64decode(s)


def make_registration_options(
    *,
    rp_id: str,
    rp_name: str,
    user_id: bytes,
    user_name: str,
    user_display_name: str,
    challenge: bytes,
    settings: Settings,
    exclude_credentials: list[PublicKeyCredentialDescriptor] | None = None,
) -> dict[str, Any]:
    """Build PublicKeyCredentialCreationOptions and return as JSON-safe dict."""
    opts = generate_registration_options(
        rp_id=rp_id,
        rp_name=rp_name,
        user_id=user_id,
        user_name=user_name,
        user_display_name=user_display_name,
        challenge=challenge,
        timeout=settings.webauthn_ttl_seconds * 1000,
        attestation=_att(settings),
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=_uv(settings),
        ),
        exclude_credentials=exclude_credentials or [],
    )
    result: dict[str, Any] = json.loads(options_to_json(opts))
    return result


def make_authentication_options(
    *,
    rp_id: str,
    challenge: bytes,
    settings: Settings,
    allow_credentials: list[PublicKeyCredentialDescriptor] | None = None,
) -> dict[str, Any]:
    """Build PublicKeyCredentialRequestOptions and return as JSON-safe dict."""
    opts = generate_authentication_options(
        rp_id=rp_id,
        challenge=challenge,
        timeout=settings.webauthn_ttl_seconds * 1000,
        user_verification=_uv(settings),
        allow_credentials=allow_credentials or [],
    )
    result: dict[str, Any] = json.loads(options_to_json(opts))
    return result


def verify_registration(
    *,
    credential_json: dict[str, Any],
    expected_challenge: bytes,
    expected_rp_id: str,
    expected_origin: str,
) -> tuple[bytes, bytes, int, str]:
    """Verify a registration response.

    Returns ``(credential_id, public_key, sign_count, aaguid)``.
    """
    cred = parse_registration_credential_json(json.dumps(credential_json))
    verified = verify_registration_response(
        credential=cred,
        expected_challenge=expected_challenge,
        expected_rp_id=expected_rp_id,
        expected_origin=expected_origin,
    )
    return (
        verified.credential_id,
        verified.credential_public_key,
        verified.sign_count,
        verified.aaguid,
    )


def verify_authentication(
    *,
    credential_json: dict[str, Any],
    expected_challenge: bytes,
    expected_rp_id: str,
    expected_origin: str,
    credential_public_key: bytes,
    credential_current_sign_count: int,
) -> tuple[bytes, int]:
    """Verify an authentication response.

    Returns ``(credential_id, new_sign_count)``.
    """
    cred = parse_authentication_credential_json(json.dumps(credential_json))
    verified = verify_authentication_response(
        credential=cred,
        expected_challenge=expected_challenge,
        expected_rp_id=expected_rp_id,
        expected_origin=expected_origin,
        credential_public_key=credential_public_key,
        credential_current_sign_count=credential_current_sign_count,
    )
    return verified.credential_id, verified.new_sign_count
