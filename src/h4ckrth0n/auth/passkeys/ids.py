"""Prefixed base32 ID generators and validators.

Scheme
------
* Generate 20 random bytes → base32-encode (lowercase, no padding) → 32 chars.
* Replace the first character with a prefix:
  - ``'u'`` for user IDs
  - ``'k'`` for internal credential (key) IDs

The WebAuthn *credential_id* from the browser is stored separately and is **not**
this internal key ID.
"""

from __future__ import annotations

import base64
import os

_ID_LEN = 32
_ALLOWED_CHARS = set("abcdefghijklmnopqrstuvwxyz234567")


def _random_base32() -> str:
    """Return a 32-char lowercase base32 string from 20 random bytes (no padding)."""
    raw = os.urandom(20)
    return base64.b32encode(raw).decode("ascii").lower()


def new_user_id() -> str:
    """Generate a user ID (32 chars, starts with ``'u'``)."""
    s = _random_base32()
    return "u" + s[1:]


def new_key_id() -> str:
    """Generate a credential key ID (32 chars, starts with ``'k'``)."""
    s = _random_base32()
    return "k" + s[1:]


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
