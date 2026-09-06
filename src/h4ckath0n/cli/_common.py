"""Shared helpers and exit codes for the operator CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from h4ckath0n.auth.authz import parse_scopes, serialize_scopes
from h4ckath0n.auth.models import User
from h4ckath0n.db.migrations.runtime import (
    create_sync_engine,
    normalize_db_url_for_sync,
)

# Exit codes
EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_BAD_ARGS = 2
EXIT_LAST_PASSKEY = 3
EXIT_MIGRATIONS_MISSING = 4
EXIT_PROD_INIT = 5


# Output helpers
def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _output(data: Any, *, fmt: str = "json", pretty: bool = False) -> None:
    if fmt == "jsonl":
        if isinstance(data, list):
            for item in data:
                print(json.dumps(item, default=str))
        else:
            print(json.dumps(data, default=str))
    else:
        indent = 2 if pretty else None
        print(json.dumps(data, default=str, indent=indent))


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _require_yes(args: argparse.Namespace) -> bool:
    if not getattr(args, "yes", False):
        _err("--yes is required for mutating commands")
        return False
    return True


# Model serializers (no secrets)
def _user_dict(user: Any) -> dict[str, Any]:
    """Serialize a User model to a safe dict (no secrets)."""
    return {
        "id": user.id,
        "role": user.role,
        "scopes": user.scopes,
        "email": user.email,
        "created_at": _iso(user.created_at),
        "disabled_at": _iso(user.disabled_at),
    }


def _device_dict(device: Any) -> dict[str, Any]:
    """Serialize a Device model to a safe dict (no public_key_jwk)."""
    return {
        "id": device.id,
        "user_id": device.user_id,
        "fingerprint": device.fingerprint,
        "label": device.label,
        "created_at": _iso(device.created_at),
        "revoked_at": _iso(device.revoked_at),
    }


def _passkey_dict(cred: Any) -> dict[str, Any]:
    """Serialize a WebAuthnCredential to a safe dict (no credential_id, public_key)."""
    return {
        "id": cred.id,
        "user_id": cred.user_id,
        "sign_count": cred.sign_count,
        "aaguid": cred.aaguid,
        "transports": cred.transports,
        "name": cred.name,
        "created_at": _iso(cred.created_at),
        "last_used_at": _iso(cred.last_used_at),
        "revoked_at": _iso(cred.revoked_at),
    }


# Database helpers
def _normalize_db_url_for_sync(url: str) -> str:
    """Backwards-compatible wrapper for tests and callers."""
    return normalize_db_url_for_sync(url)


def _get_db_url(args: argparse.Namespace) -> str:
    """Resolve the database URL from --db flag or environment."""
    if getattr(args, "db", None):
        return str(args.db)
    return os.environ.get("H4CKATH0N_DATABASE_URL", "sqlite:///./h4ckath0n.db")


def _make_sync_engine(url: str) -> Engine:
    return create_sync_engine(url)


@contextmanager
def _sync_session(args: argparse.Namespace) -> Iterator[Session]:
    """Yield a synchronous Session, disposing the engine afterwards."""
    url = _normalize_db_url_for_sync(_get_db_url(args))
    engine = _make_sync_engine(url)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


def _normalize_scopes(raw: str) -> str:
    """Normalize a comma-separated scopes string."""
    return serialize_scopes(parse_scopes(raw))


def _selection_provided(args: argparse.Namespace) -> bool:
    """True when a user selector (--user-id or --email) was supplied."""
    return bool(getattr(args, "user_id", None) or getattr(args, "email", None))


def _resolve_user(session: Session, args: argparse.Namespace) -> User | None:
    """Resolve a user by --user-id or --email. Returns user or None."""
    from sqlalchemy import select

    user_id = getattr(args, "user_id", None)
    email = getattr(args, "email", None)

    if (user_id and email) or (not user_id and not email):
        _err("specify exactly one of --user-id or --email")
        return None

    if user_id:
        return session.get(User, user_id)

    stmt = select(User).where(User.email == email)
    return session.scalar(stmt)


def _user_or_exit(
    session: Session, args: argparse.Namespace
) -> tuple[User | None, int | None]:
    """Resolve a user or return the appropriate exit code.

    Returns ``(user, None)`` on success, or ``(None, exit_code)`` where the
    error message has already been printed to stderr.
    """
    user = _resolve_user(session, args)
    if user is not None:
        return user, None
    if not _selection_provided(args):
        return None, EXIT_BAD_ARGS
    _err("user not found")
    return None, EXIT_NOT_FOUND


def _add_user_selector(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--user-id", default=None, help="User ID (u...)")
    group.add_argument("--email", default=None, help="User email")
