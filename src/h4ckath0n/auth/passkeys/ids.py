"""Prefixed base32 ID generators and validators.

Scheme
------
* Generate N random bytes -> base32-encode (lowercase, no padding).
* Replace the first character with a prefix:
  - 'u' for user IDs
  - 'k' for internal credential (key) IDs
  - 'd' for device IDs

Implementation notes
--------------------
* Per-thread XOF reader using cryptography's XOFHash(SHAKE128).
* A process-wide master key is generated from os.urandom(32) at import/startup.
* Stream input is domain-separated and bound to (master_key, tid, per-reader OS randomness).
* Fork safety: clear thread-local cached reader in the child via os.register_at_fork so the
  child never reuses an inherited XOF state. If the fork hook cannot be installed, we fall
  back to PID checking and emit a warning on platforms that support fork.
"""

from __future__ import annotations

import base64
import contextlib
import os
import sys
import threading
import warnings

from cryptography.hazmat.primitives import hashes

_ID_LEN = 32
_ALLOWED_CHARS = set("abcdefghijklmnopqrstuvwxyz234567")

# Domain separation for this particular PRNG stream.
_DOMAIN = b"h4ckath0n:idgen:v1\x00"

# No env override, always generate from OS at startup/import time.
_MASTER_KEY = os.urandom(32)

_tls = threading.local()

_U64_MASK = (1 << 64) - 1


def _u64le(x: int) -> bytes:
    # threading.get_ident() and os.getpid() are expected to be non-negative in practice.
    # Mask defensively so we never raise OverflowError for unusually large values.
    return (x & _U64_MASK).to_bytes(8, "little", signed=False)


def _clear_tls_after_fork_child() -> None:
    # After fork, the child inherits thread-local objects and their internal XOF state.
    # Clearing forces a rebuild and immediate divergence in the child.
    with contextlib.suppress(Exception):
        _tls.__dict__.clear()


_FORK_HOOK_INSTALLED = False
try:
    os.register_at_fork(after_in_child=_clear_tls_after_fork_child)
    _FORK_HOOK_INSTALLED = True
except AttributeError:
    # register_at_fork is not available on this Python or platform.
    _FORK_HOOK_INSTALLED = False
except Exception:
    # Best-effort, if registration fails we still keep a safe fallback below.
    _FORK_HOOK_INSTALLED = False

if not _FORK_HOOK_INSTALLED and hasattr(os, "fork"):
    warnings.warn(
        "Fork-safety hook (os.register_at_fork) is unavailable. This module will fall back to "
        "PID checking to avoid reusing inherited XOF state after fork, which adds a small "
        "per-call overhead. If you later remove the PID fallback and still fork, ID collisions "
        "can occur because the child can inherit the parent's XOF stream state.",
        RuntimeWarning,
        stacklevel=2,
    )


class _ShakeXOFReader:
    __slots__ = ("_xof",)

    def __init__(self, tid: int) -> None:
        alg = hashes.SHAKE128(digest_size=sys.maxsize)
        xof = hashes.XOFHash(alg)

        # Bind this per-thread stream to: domain || master_key || tid || randombytes(16)
        xof.update(_DOMAIN)
        xof.update(_MASTER_KEY)
        xof.update(_u64le(tid))
        xof.update(os.urandom(16))  # Extra per-reader randomness from the OS.

        self._xof = xof

    def read(self, nbytes: int) -> bytes:
        if nbytes < 0:
            raise ValueError("nbytes must be >= 0")
        return self._xof.squeeze(nbytes)


def _thread_reader() -> _ShakeXOFReader:
    reader = getattr(_tls, "reader", None)
    if reader is not None:
        if _FORK_HOOK_INSTALLED:
            return reader
        # Fallback safety if we could not install a fork hook: detect fork by PID change.
        pid = os.getpid()
        if getattr(_tls, "pid", None) == pid:
            return reader

    tid = threading.get_ident()
    reader = _ShakeXOFReader(tid)
    _tls.reader = reader
    if not _FORK_HOOK_INSTALLED:
        _tls.pid = os.getpid()
    return reader


def random_bytes(nbytes: int) -> bytes:
    """Return *nbytes* random bytes from the per-thread XOF stream.

    This is the shared primitive used by higher-level ID helpers.
    """
    if nbytes <= 0:
        raise ValueError("nbytes must be > 0")
    return _thread_reader().read(nbytes)


def random_base32(nbytes: int = 20) -> str:
    """Return a lowercase base32 string (no padding) from *nbytes* random bytes.

    Notes
    -----
    * For nbytes=20, the output length is 32 characters, which matches this module's ID scheme.
    * To avoid '=' padding in RFC 4648 base32, nbytes must be a multiple of 5.
    """
    if nbytes % 5 != 0:
        raise ValueError("nbytes must be a multiple of 5 to avoid base32 padding")
    raw = random_bytes(nbytes)
    return base64.b32encode(raw).decode("ascii").lower()


def new_user_id() -> str:
    """Generate a user ID (32 chars, starts with 'u')."""
    s = random_base32()
    return "u" + s[1:]


def new_key_id() -> str:
    """Generate a credential key ID (32 chars, starts with 'k')."""
    s = random_base32()
    return "k" + s[1:]


def new_device_id() -> str:
    """Generate a device ID (32 chars, starts with 'd')."""
    s = random_base32()
    return "d" + s[1:]


def new_token_id() -> str:
    """Generate a generic token/row ID (128-bit random hex, 32 chars)."""
    return random_bytes(16).hex()


def is_user_id(value: str) -> bool:
    """Return True when *value* looks like a valid user ID."""
    return (
        len(value) == _ID_LEN and value[:1] == "u" and all(c in _ALLOWED_CHARS for c in value[1:])
    )


def is_key_id(value: str) -> bool:
    """Return True when *value* looks like a valid key ID."""
    return (
        len(value) == _ID_LEN and value[:1] == "k" and all(c in _ALLOWED_CHARS for c in value[1:])
    )


def is_device_id(value: str) -> bool:
    """Return True when *value* looks like a valid device ID."""
    return (
        len(value) == _ID_LEN and value[:1] == "d" and all(c in _ALLOWED_CHARS for c in value[1:])
    )
