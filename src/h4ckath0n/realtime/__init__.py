"""Realtime authentication and streaming helpers for WebSocket and SSE.

Provides protocol-aware device-JWT verification with mandatory ``aud``
(audience) binding so tokens cannot be confused across HTTP, WebSocket,
and SSE channels.

Usage constants
~~~~~~~~~~~~~~~
* ``AUD_HTTP``  – ``"h4ckath0n:http"``
* ``AUD_WS``   – ``"h4ckath0n:ws"``
* ``AUD_SSE``  – ``"h4ckath0n:sse"``
"""

from h4ckath0n.realtime.auth import (
    AUD_HTTP,
    AUD_SSE,
    AUD_WS,
    AuthContext,
    AuthError,
    authenticate_http_request,
    authenticate_sse_request,
    authenticate_websocket,
    verify_device_jwt,
)
from h4ckath0n.realtime.sse import sse_response

__all__ = [
    "AUD_HTTP",
    "AUD_SSE",
    "AUD_WS",
    "AuthContext",
    "AuthError",
    "authenticate_http_request",
    "authenticate_sse_request",
    "authenticate_websocket",
    "sse_response",
    "verify_device_jwt",
]
