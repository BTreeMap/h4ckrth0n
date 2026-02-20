"""Passkey (WebAuthn) authentication – default auth method for h4ckath0n."""

from h4ckath0n.auth.passkeys.ids import (
    is_device_id,
    is_key_id,
    is_user_id,
    new_device_id,
    new_key_id,
    new_token_id,
    new_user_id,
    random_base32,
    random_bytes,
)

__all__ = [
    "random_bytes",
    "random_base32",
    "new_user_id",
    "new_key_id",
    "new_device_id",
    "new_token_id",
    "is_user_id",
    "is_key_id",
    "is_device_id",
]
