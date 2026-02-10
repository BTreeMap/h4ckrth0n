"""Prefixed base32 ID generators and validators.

Scheme
------
* Generate 20 random bytes → base32-encode (lowercase, strip padding) → 32 chars.
* Replace the first character with a prefix:
  - ``'u'`` for user IDs
  - ``'k'`` for internal credential (key) IDs

The WebAuthn *credential_id* from the browser is stored separately and is **not**
this internal key ID.
"""

from __future__ import annotations

import base64
import os
import uuid

_ID_LEN = 32
_ALLOWED_CHARS = set("abcdefghijklmnopqrstuvwxyz234567")


def _random_base32() -> str:
    """Return a 32-char lowercase base32 string from 20 random bytes."""
    raw = os.urandom(20)
    return base64.b32encode(raw).decode("ascii").lower().rstrip("=")


def new_user_id() -> str:
    """Generate a user ID (32 chars, starts with ``'u'``)."""
    s = _random_base32()
    return "u" + s[1:]


def new_key_id() -> str:
    """Generate a credential key ID (32 chars, starts with ``'k'``)."""
    s = _random_base32()
    return "k" + s[1:]


def new_token_id() -> str:
    """Generate a generic token/row ID (UUID hex, 32 chars)."""
    return uuid.uuid4().hex


def is_user_id(value: str) -> bool:
    """Return ``True`` when *value* looks like a valid user ID."""
    if len(value) != _ID_LEN:
        return False
    if value[0] != "u":
        return False
    return all(c in _ALLOWED_CHARS for c in value[1:])


def is_key_id(value: str) -> bool:
    """Return ``True`` when *value* looks like a valid key ID."""
    if len(value) != _ID_LEN:
        return False
    if value[0] != "k":
        return False
    return all(c in _ALLOWED_CHARS for c in value[1:])


def new_device_id() -> str:
    """Generate a device ID (32 chars, starts with ``'d'``)."""
    s = _random_base32()
    return "d" + s[1:]


def is_device_id(value: str) -> bool:
    """Return ``True`` when *value* looks like a valid device ID."""
    if len(value) != _ID_LEN:
        return False
    if value[0] != "d":
        return False
    return all(c in _ALLOWED_CHARS for c in value[1:])
