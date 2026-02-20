"""Prefixed base32 ID generators and validators.

Scheme
------
* Generate N random bytes -> base32-encode (lowercase, strip padding).
* Replace the first character with a prefix:
  - 'u' for user IDs
  - 'k' for internal credential (key) IDs
  - 'd' for device IDs

Implementation notes
--------------------
* Per-thread XOF reader using cryptography's XOFHash(SHAKE128).
* A process-wide master key is generated from os.urandom(32) at import/startup.
* Stream input is domain-separated and bound to (master_key, pid, tid).
* Fork safety: if PID changes, rebuild the reader so the child diverges immediately.
"""

from __future__ import annotations

import base64
import os
import sys
import threading
import uuid

from cryptography.hazmat.primitives import hashes

_ID_LEN = 32
_ALLOWED_CHARS = set("abcdefghijklmnopqrstuvwxyz234567")

# Domain separation for this particular PRNG stream.
_DOMAIN = b"h4ckath0n:idgen:v1"

# No env override: always generate from OS at startup/import time.
_MASTER_KEY = os.urandom(32)

_tls = threading.local()


def _u64le(x: int) -> bytes:
    # os.getpid() and threading.get_ident() are expected to be non-negative in practice.
    return x.to_bytes(8, "little", signed=False)


class _ShakeXOFReader:
    __slots__ = ("_xof",)

    def __init__(self, pid: int, tid: int) -> None:
        # SHAKE128 is plenty for "unpredictable IDs" and typically faster than SHAKE256.
        # digest_size here is the maximum total bytes that can be squeezed.
        alg = hashes.SHAKE128(digest_size=sys.maxsize)
        xof = hashes.XOFHash(alg)

        # Bind this per-thread stream to: domain || master_key || pid || tid
        xof.update(_DOMAIN)
        xof.update(_MASTER_KEY)
        xof.update(_u64le(pid))
        xof.update(_u64le(tid))

        # After squeeze() is called once, XOFHash cannot be updated anymore.
        # This reader only calls squeeze(), so it's safe.
        self._xof = xof

    def read(self, nbytes: int) -> bytes:
        if nbytes < 0:
            raise ValueError("nbytes must be >= 0")
        return self._xof.squeeze(nbytes)


def _thread_reader() -> _ShakeXOFReader:
    pid = os.getpid()

    # Fast path: same process, reuse per-thread reader.
    reader = getattr(_tls, "reader", None)
    if reader is not None and getattr(_tls, "pid", None) == pid:
        return reader

    # Slow path: first use in this thread, or fork detected (PID changed).
    tid = threading.get_ident()
    reader = _ShakeXOFReader(pid, tid)
    _tls.pid = pid
    _tls.reader = reader
    return reader


def random_base32(nbytes: int = 20) -> str:
    """Return a lowercase base32 string (no padding) from *nbytes* of XOF output.

    Notes
    -----
    * For nbytes=20, the output length is 32 characters, which matches this module's ID scheme.
    * For other values, the string length will be ceil(nbytes * 8 / 5).
    """
    if nbytes <= 0:
        raise ValueError("nbytes must be > 0")
    raw = _thread_reader().read(nbytes)
    return base64.b32encode(raw).decode("ascii").lower().rstrip("=")


def new_user_id() -> str:
    """Generate a user ID (32 chars, starts with ``'u'``)."""
    s = random_base32()
    return "u" + s[1:]


def new_key_id() -> str:
    """Generate a credential key ID (32 chars, starts with ``'k'``)."""
    s = random_base32()
    return "k" + s[1:]


def new_device_id() -> str:
    """Generate a device ID (32 chars, starts with ``'d'``)."""
    s = random_base32()
    return "d" + s[1:]


def new_token_id() -> str:
    """Generate a generic token/row ID (UUID hex, 32 chars)."""
    return uuid.uuid4().hex


def is_user_id(value: str) -> bool:
    """Return ``True`` when *value* looks like a valid user ID."""
    return (
        len(value) == _ID_LEN
        and value[:1] == "u"
        and all(c in _ALLOWED_CHARS for c in value[1:])
    )


def is_key_id(value: str) -> bool:
    """Return ``True`` when *value* looks like a valid key ID."""
    return (
        len(value) == _ID_LEN
        and value[:1] == "k"
        and all(c in _ALLOWED_CHARS for c in value[1:])
    )


def is_device_id(value: str) -> bool:
    """Return ``True`` when *value* looks like a valid device ID."""
    return (
        len(value) == _ID_LEN
        and value[:1] == "d"
        and all(c in _ALLOWED_CHARS for c in value[1:])
    )
