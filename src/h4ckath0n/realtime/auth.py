"""Protocol-aware device-JWT verification.

All three transports (HTTP, WebSocket, SSE) share the same core
verification logic via :func:`verify_device_jwt`.  Each transport
helper merely extracts the raw JWT from the appropriate location
and calls the core verifier with the correct ``expected_aud``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import jwt
from cryptography.hazmat.primitives import serialization
from fastapi import WebSocket
from jwt.algorithms import ECAlgorithm
from sqlalchemy.orm import Session
from starlette.requests import Request

from h4ckath0n.auth.jwt import decode_device_token, get_unverified_kid
from h4ckath0n.auth.models import Device, User

# ── Audience constants ────────────────────────────────────────────────────

AUD_HTTP = "h4ckath0n:http"
AUD_WS = "h4ckath0n:ws"
AUD_SSE = "h4ckath0n:sse"


# ── AuthContext (returned on success) ─────────────────────────────────────


@dataclass(frozen=True, slots=True)
class AuthContext:
    """Minimal authenticated identity returned by the verifier."""

    user_id: str
    device_id: str


# ── Core verifier ─────────────────────────────────────────────────────────


class AuthError(Exception):
    """Raised when device-JWT verification fails."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def _get_db(app_state: object) -> Session:
    return app_state.session_factory()  # type: ignore[attr-defined, no-any-return]


def verify_device_jwt(
    raw_jwt: str,
    *,
    expected_aud: str,
    db: Session,
) -> AuthContext:
    """Verify a device-signed ES256 JWT and enforce ``aud`` binding.

    Parameters
    ----------
    raw_jwt:
        The raw JWT string (never logged).
    expected_aud:
        Required ``aud`` value (``AUD_HTTP``, ``AUD_WS`` or ``AUD_SSE``).
    db:
        An open SQLAlchemy session.

    Returns
    -------
    AuthContext
        Contains ``user_id`` and ``device_id`` on success.

    Raises
    ------
    AuthError
        On any verification failure.
    """
    kid = get_unverified_kid(raw_jwt)
    if not kid:
        raise AuthError("Missing kid in JWT header")

    device = db.query(Device).filter(Device.id == kid).first()
    if not device:
        raise AuthError("Unknown device")

    try:
        jwk_dict = json.loads(device.public_key_jwk)
        public_key = ECAlgorithm(ECAlgorithm.SHA256).from_jwk(jwk_dict)
        pem = public_key.public_bytes(  # type: ignore[union-attr]
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()
    except (ValueError, KeyError, TypeError):
        raise AuthError("Invalid device key") from None

    try:
        claims = decode_device_token(raw_jwt, public_key_pem=pem)
    except jwt.ExpiredSignatureError:
        raise AuthError("Token expired") from None
    except jwt.InvalidTokenError:
        raise AuthError("Invalid token") from None

    # ── aud enforcement ───────────────────────────────────────────────
    if not claims.aud:
        raise AuthError("Missing aud claim")
    if claims.aud != expected_aud:
        raise AuthError(f"Invalid aud: expected {expected_aud}")

    # ── user lookup ───────────────────────────────────────────────────
    user = db.query(User).filter(User.id == claims.sub).first()
    if user is None:
        raise AuthError("User not found")

    return AuthContext(user_id=user.id, device_id=device.id)


# ── Transport helpers ─────────────────────────────────────────────────────


def authenticate_http_request(request: Request) -> AuthContext:
    """Authenticate an HTTP request using ``Authorization: Bearer <jwt>``.

    Enforces ``aud = h4ckath0n:http``.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise AuthError("Missing Authorization header")
    raw_jwt = auth_header[7:]

    db: Session = _get_db(request.app.state)
    try:
        return verify_device_jwt(raw_jwt, expected_aud=AUD_HTTP, db=db)
    finally:
        db.close()


def authenticate_sse_request(request: Request) -> AuthContext:
    """Authenticate an SSE request using ``Authorization: Bearer <jwt>``.

    Enforces ``aud = h4ckath0n:sse``.  Falls back to ``?token=`` query
    param for manual debugging only (not used by the web template).
    """
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        raw_jwt = auth_header[7:]
    else:
        raw_jwt = request.query_params.get("token", "")
    if not raw_jwt:
        raise AuthError("Missing token")

    db: Session = _get_db(request.app.state)
    try:
        return verify_device_jwt(raw_jwt, expected_aud=AUD_SSE, db=db)
    finally:
        db.close()


async def authenticate_websocket(websocket: WebSocket) -> AuthContext:
    """Authenticate a WebSocket using the ``token`` query parameter.

    Enforces ``aud = h4ckath0n:ws``.

    The caller **must** close the connection with code 1008 if this
    raises :class:`AuthError`.  The connection is **not** accepted here.
    """
    raw_jwt = websocket.query_params.get("token", "")
    if not raw_jwt:
        raise AuthError("Missing token")

    db: Session = _get_db(websocket.app.state)
    try:
        return verify_device_jwt(raw_jwt, expected_aud=AUD_WS, db=db)
    finally:
        db.close()
