"""Argon2id password hashing."""

from __future__ import annotations

from typing import cast

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash *password* with Argon2id."""
    return cast(str, _ph.hash(password))


def verify_password(password: str, hash_: str) -> bool:
    """Verify *password* against an Argon2id *hash_*."""
    try:
        return cast(bool, _ph.verify(hash_, password))
    except VerifyMismatchError:
        return False
