"""h4ckath0n operator CLI.

Provides ``h4ckath0n`` console script and ``python -m h4ckath0n`` entry point.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from typing import Any

from alembic import command as alembic_command
from alembic.config import Config

from h4ckath0n.db.migrations.runtime import (
    PackagedMigrationsError,
    create_sync_engine,
    get_schema_status,
    normalize_db_url_for_sync,
    packaged_migrations_dir,
    run_upgrade_to_head,
)

# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------
EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_BAD_ARGS = 2
EXIT_LAST_PASSKEY = 3
EXIT_MIGRATIONS_MISSING = 4
EXIT_PROD_INIT = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _user_dict(user: Any) -> dict:
    """Serialize a User model to a safe dict (no secrets)."""
    return {
        "id": user.id,
        "role": user.role,
        "scopes": user.scopes,
        "email": user.email,
        "created_at": _iso(user.created_at),
        "disabled_at": _iso(user.disabled_at),
    }


def _device_dict(device: Any) -> dict:
    """Serialize a Device model to a safe dict (no public_key_jwk)."""
    return {
        "id": device.id,
        "user_id": device.user_id,
        "fingerprint": device.fingerprint,
        "label": device.label,
        "created_at": _iso(device.created_at),
        "revoked_at": _iso(device.revoked_at),
    }


def _passkey_dict(cred: Any) -> dict:
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


def _normalize_db_url_for_sync(url: str) -> str:
    """Backwards-compatible wrapper for tests and callers."""
    return normalize_db_url_for_sync(url)


def _get_db_url(args: argparse.Namespace) -> str:
    """Resolve the database URL from --db flag or environment."""
    if getattr(args, "db", None):
        return str(args.db)
    return os.environ.get("H4CKATH0N_DATABASE_URL", "sqlite:///./h4ckath0n.db")


def _make_sync_engine(url: str):  # type: ignore[no-untyped-def]
    return create_sync_engine(url)


def _normalize_scopes(raw: str) -> str:
    """Normalize a comma-separated scopes string."""
    parts = [s.strip() for s in raw.split(",")]
    parts = [s for s in parts if s]
    # de-duplicate preserving order
    seen: set[str] = set()
    result: list[str] = []
    for s in parts:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return ",".join(result)


def _resolve_user(session: Any, args: argparse.Namespace):  # type: ignore[no-untyped-def]
    """Resolve a user by --user-id or --email. Returns user or None."""
    from sqlalchemy import select

    from h4ckath0n.auth.models import User

    user_id = getattr(args, "user_id", None)
    email = getattr(args, "email", None)

    if user_id and email:
        _err("specify exactly one of --user-id or --email")
        return None
    if not user_id and not email:
        _err("specify exactly one of --user-id or --email")
        return None

    if user_id:
        stmt = select(User).where(User.id == user_id)
    else:
        stmt = select(User).where(User.email == email)

    return session.execute(stmt).scalars().first()


# ---------------------------------------------------------------------------
# DB commands
# ---------------------------------------------------------------------------


def _cmd_db_ping(args: argparse.Namespace) -> int:
    url = _normalize_db_url_for_sync(_get_db_url(args))
    engine = _make_sync_engine(url)
    try:
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        try:
            status = get_schema_status(url)
            _output(
                {
                    "ok": True,
                    "schema_state": status.state,
                    "current_revisions": list(status.current_revisions),
                    "head_revisions": list(status.head_revisions),
                    "warning": status.warning,
                },
                fmt=args.format,
                pretty=args.pretty,
            )
        except PackagedMigrationsError:
            _err("packaged migrations not found; installation may be broken")
            return EXIT_MIGRATIONS_MISSING
        return EXIT_OK
    finally:
        engine.dispose()


def _cmd_db_migrate_upgrade(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    url = _normalize_db_url_for_sync(_get_db_url(args))
    revision = getattr(args, "to", "head")
    try:
        if revision == "head":
            # Using our high-level helper which handles fresh install nicely
            run_upgrade_to_head(url)
        else:
            with packaged_migrations_dir() as migrations_path:
                cfg = Config()
                cfg.set_main_option("script_location", str(migrations_path))
                cfg.set_main_option("sqlalchemy.url", url)
                alembic_command.upgrade(cfg, revision)
        _output({"ok": True, "revision": revision}, fmt=args.format, pretty=args.pretty)
        return EXIT_OK
    except PackagedMigrationsError:
        _err("packaged migrations not found; installation may be broken")
        return EXIT_MIGRATIONS_MISSING


def _cmd_db_migrate_downgrade(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    url = _normalize_db_url_for_sync(_get_db_url(args))

    revision = getattr(args, "to", None)
    if not revision:
        _err("--to is required for downgrade")
        return EXIT_BAD_ARGS

    try:
        with packaged_migrations_dir() as migrations_path:
            cfg = Config()
            cfg.set_main_option("script_location", str(migrations_path))
            cfg.set_main_option("sqlalchemy.url", url)
            alembic_command.downgrade(cfg, revision)
        _output({"ok": True, "revision": revision}, fmt=args.format, pretty=args.pretty)
        return EXIT_OK
    except PackagedMigrationsError:
        _err("packaged migrations not found; installation may be broken")
        return EXIT_MIGRATIONS_MISSING


def _cmd_db_migrate_current(args: argparse.Namespace) -> int:
    url = _normalize_db_url_for_sync(_get_db_url(args))
    try:
        with packaged_migrations_dir() as migrations_path:
            cfg = Config()
            cfg.set_main_option("script_location", str(migrations_path))
            cfg.set_main_option("sqlalchemy.url", url)
            alembic_command.current(cfg)
        return EXIT_OK
    except PackagedMigrationsError:
        _err("packaged migrations not found; installation may be broken")
        return EXIT_MIGRATIONS_MISSING


def _cmd_db_migrate_heads(args: argparse.Namespace) -> int:
    url = _normalize_db_url_for_sync(_get_db_url(args))
    try:
        with packaged_migrations_dir() as migrations_path:
            cfg = Config()
            cfg.set_main_option("script_location", str(migrations_path))
            cfg.set_main_option("sqlalchemy.url", url)
            alembic_command.heads(cfg)
        return EXIT_OK
    except PackagedMigrationsError:
        _err("packaged migrations not found; installation may be broken")
        return EXIT_MIGRATIONS_MISSING


# ---------------------------------------------------------------------------
# Users commands
# ---------------------------------------------------------------------------


def _cmd_users_list(args: argparse.Namespace) -> int:
    from sqlalchemy import select

    from h4ckath0n.auth.models import User

    url = _normalize_db_url_for_sync(_get_db_url(args))
    engine = _make_sync_engine(url)
    try:
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            stmt = select(User)
            if not getattr(args, "include_disabled", False):
                stmt = stmt.where(User.disabled_at.is_(None))
            stmt = stmt.offset(args.offset).limit(args.limit)
            users = session.execute(stmt).scalars().all()
            _output([_user_dict(u) for u in users], fmt=args.format, pretty=args.pretty)
        return EXIT_OK
    finally:
        engine.dispose()


def _cmd_users_show(args: argparse.Namespace) -> int:
    from sqlalchemy import func, select

    from h4ckath0n.auth.models import Device, WebAuthnCredential

    url = _normalize_db_url_for_sync(_get_db_url(args))
    engine = _make_sync_engine(url)
    try:
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            user = _resolve_user(session, args)
            if user is None:
                if not (getattr(args, "user_id", None) or getattr(args, "email", None)):
                    return EXIT_BAD_ARGS
                _err("user not found")
                return EXIT_NOT_FOUND

            data = _user_dict(user)

            # Device counts
            total_devices = (
                session.execute(
                    select(func.count()).select_from(Device).where(Device.user_id == user.id)
                ).scalar()
                or 0
            )
            active_devices = (
                session.execute(
                    select(func.count())
                    .select_from(Device)
                    .where(Device.user_id == user.id, Device.revoked_at.is_(None))
                ).scalar()
                or 0
            )

            # Passkey counts
            total_passkeys = (
                session.execute(
                    select(func.count())
                    .select_from(WebAuthnCredential)
                    .where(WebAuthnCredential.user_id == user.id)
                ).scalar()
                or 0
            )
            active_passkeys = (
                session.execute(
                    select(func.count())
                    .select_from(WebAuthnCredential)
                    .where(
                        WebAuthnCredential.user_id == user.id,
                        WebAuthnCredential.revoked_at.is_(None),
                    )
                ).scalar()
                or 0
            )

            data["devices_total"] = total_devices
            data["devices_active"] = active_devices
            data["passkeys_total"] = total_passkeys
            data["passkeys_active"] = active_passkeys

            _output(data, fmt=args.format, pretty=args.pretty)
        return EXIT_OK
    finally:
        engine.dispose()


def _cmd_users_set_role(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    url = _normalize_db_url_for_sync(_get_db_url(args))
    engine = _make_sync_engine(url)
    try:
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            user = _resolve_user(session, args)
            if user is None:
                if not (getattr(args, "user_id", None) or getattr(args, "email", None)):
                    return EXIT_BAD_ARGS
                _err("user not found")
                return EXIT_NOT_FOUND

            user.role = args.role
            session.commit()
            session.refresh(user)
            _output(_user_dict(user), fmt=args.format, pretty=args.pretty)
        return EXIT_OK
    finally:
        engine.dispose()


def _cmd_users_disable(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    url = _normalize_db_url_for_sync(_get_db_url(args))
    engine = _make_sync_engine(url)
    try:
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            user = _resolve_user(session, args)
            if user is None:
                if not (getattr(args, "user_id", None) or getattr(args, "email", None)):
                    return EXIT_BAD_ARGS
                _err("user not found")
                return EXIT_NOT_FOUND

            user.disabled_at = datetime.now(UTC)
            session.commit()
            session.refresh(user)
            _output(_user_dict(user), fmt=args.format, pretty=args.pretty)
        return EXIT_OK
    finally:
        engine.dispose()


def _cmd_users_enable(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    url = _normalize_db_url_for_sync(_get_db_url(args))
    engine = _make_sync_engine(url)
    try:
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            user = _resolve_user(session, args)
            if user is None:
                if not (getattr(args, "user_id", None) or getattr(args, "email", None)):
                    return EXIT_BAD_ARGS
                _err("user not found")
                return EXIT_NOT_FOUND

            user.disabled_at = None
            session.commit()
            session.refresh(user)
            _output(_user_dict(user), fmt=args.format, pretty=args.pretty)
        return EXIT_OK
    finally:
        engine.dispose()


def _cmd_users_scopes_add(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    url = _normalize_db_url_for_sync(_get_db_url(args))
    engine = _make_sync_engine(url)
    try:
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            user = _resolve_user(session, args)
            if user is None:
                if not (getattr(args, "user_id", None) or getattr(args, "email", None)):
                    return EXIT_BAD_ARGS
                _err("user not found")
                return EXIT_NOT_FOUND

            existing = set(s for s in user.scopes.split(",") if s.strip())
            for scope in args.scope:
                existing.add(scope.strip())
            user.scopes = _normalize_scopes(",".join(existing))
            session.commit()
            session.refresh(user)
            _output(_user_dict(user), fmt=args.format, pretty=args.pretty)
        return EXIT_OK
    finally:
        engine.dispose()


def _cmd_users_scopes_remove(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    url = _normalize_db_url_for_sync(_get_db_url(args))
    engine = _make_sync_engine(url)
    try:
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            user = _resolve_user(session, args)
            if user is None:
                if not (getattr(args, "user_id", None) or getattr(args, "email", None)):
                    return EXIT_BAD_ARGS
                _err("user not found")
                return EXIT_NOT_FOUND

            existing = [s for s in user.scopes.split(",") if s.strip()]
            to_remove = {s.strip() for s in args.scope}
            remaining = [s for s in existing if s not in to_remove]
            user.scopes = _normalize_scopes(",".join(remaining))
            session.commit()
            session.refresh(user)
            _output(_user_dict(user), fmt=args.format, pretty=args.pretty)
        return EXIT_OK
    finally:
        engine.dispose()


def _cmd_users_scopes_set(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    url = _normalize_db_url_for_sync(_get_db_url(args))
    engine = _make_sync_engine(url)
    try:
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            user = _resolve_user(session, args)
            if user is None:
                if not (getattr(args, "user_id", None) or getattr(args, "email", None)):
                    return EXIT_BAD_ARGS
                _err("user not found")
                return EXIT_NOT_FOUND

            user.scopes = _normalize_scopes(args.scopes)
            session.commit()
            session.refresh(user)
            _output(_user_dict(user), fmt=args.format, pretty=args.pretty)
        return EXIT_OK
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# Devices commands
# ---------------------------------------------------------------------------


def _cmd_devices_list(args: argparse.Namespace) -> int:
    from sqlalchemy import select

    from h4ckath0n.auth.models import Device

    url = _normalize_db_url_for_sync(_get_db_url(args))
    engine = _make_sync_engine(url)
    try:
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            user = _resolve_user(session, args)
            if user is None:
                if not (getattr(args, "user_id", None) or getattr(args, "email", None)):
                    return EXIT_BAD_ARGS
                _err("user not found")
                return EXIT_NOT_FOUND

            stmt = select(Device).where(Device.user_id == user.id)
            if not getattr(args, "include_revoked", False):
                stmt = stmt.where(Device.revoked_at.is_(None))
            devices = session.execute(stmt).scalars().all()
            _output([_device_dict(d) for d in devices], fmt=args.format, pretty=args.pretty)
        return EXIT_OK
    finally:
        engine.dispose()


def _cmd_devices_revoke(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    from sqlalchemy import select

    from h4ckath0n.auth.models import Device

    url = _normalize_db_url_for_sync(_get_db_url(args))
    engine = _make_sync_engine(url)
    try:
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            stmt = select(Device).where(Device.id == args.device_id)
            device = session.execute(stmt).scalars().first()
            if device is None:
                _err("device not found")
                return EXIT_NOT_FOUND

            if device.revoked_at is None:
                device.revoked_at = datetime.now(UTC)
                session.commit()
                session.refresh(device)
            _output(_device_dict(device), fmt=args.format, pretty=args.pretty)
        return EXIT_OK
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# Passkeys commands
# ---------------------------------------------------------------------------


def _cmd_passkeys_list(args: argparse.Namespace) -> int:
    from sqlalchemy import select

    from h4ckath0n.auth.models import WebAuthnCredential

    url = _normalize_db_url_for_sync(_get_db_url(args))
    engine = _make_sync_engine(url)
    try:
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            user = _resolve_user(session, args)
            if user is None:
                if not (getattr(args, "user_id", None) or getattr(args, "email", None)):
                    return EXIT_BAD_ARGS
                _err("user not found")
                return EXIT_NOT_FOUND

            stmt = select(WebAuthnCredential).where(WebAuthnCredential.user_id == user.id)
            if not getattr(args, "include_revoked", False):
                stmt = stmt.where(WebAuthnCredential.revoked_at.is_(None))
            creds = session.execute(stmt).scalars().all()
            _output([_passkey_dict(c) for c in creds], fmt=args.format, pretty=args.pretty)
        return EXIT_OK
    finally:
        engine.dispose()


def _cmd_passkeys_revoke(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    from sqlalchemy import func, select

    from h4ckath0n.auth.models import WebAuthnCredential

    url = _normalize_db_url_for_sync(_get_db_url(args))
    engine = _make_sync_engine(url)
    try:
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            stmt = select(WebAuthnCredential).where(WebAuthnCredential.id == args.key_id)
            cred = session.execute(stmt).scalars().first()
            if cred is None:
                _err("passkey not found")
                return EXIT_NOT_FOUND

            if cred.revoked_at is not None:
                _err("passkey already revoked")
                return EXIT_BAD_ARGS

            # Check last-passkey invariant
            active_count = (
                session.execute(
                    select(func.count())
                    .select_from(WebAuthnCredential)
                    .where(
                        WebAuthnCredential.user_id == cred.user_id,
                        WebAuthnCredential.revoked_at.is_(None),
                    )
                ).scalar()
                or 0
            )

            if active_count <= 1:
                _err("refusing to revoke the last active passkey")
                return EXIT_LAST_PASSKEY

            cred.revoked_at = datetime.now(UTC)
            session.commit()
            session.refresh(cred)
            _output(_passkey_dict(cred), fmt=args.format, pretty=args.pretty)
        return EXIT_OK
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# User-selector arguments helper
# ---------------------------------------------------------------------------


def _add_user_selector(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--user-id", default=None, help="User ID (u...)")
    group.add_argument("--email", default=None, help="User email")


# ---------------------------------------------------------------------------
# Argument parser construction
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    # Common flags shared by all leaf subcommands
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", default=None, help="Database URL override")
    common.add_argument(
        "--format", choices=["json", "jsonl"], default="json", help="Output format"
    )
    common.add_argument("--pretty", action="store_true", default=False, help="Pretty-print output")

    parser = argparse.ArgumentParser(
        prog="h4ckath0n",
        description="h4ckath0n operator CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    # ---- db ----
    db_parser = subparsers.add_parser("db", help="Database operations")
    db_sub = db_parser.add_subparsers(dest="db_command")

    # db ping
    db_sub.add_parser("ping", parents=[common], help="Check database connectivity")

    # db init -> REMOVED
    # db migrate
    db_migrate = db_sub.add_parser("migrate", help="Run Alembic migrations")
    migrate_sub = db_migrate.add_subparsers(dest="migrate_command")

    # db migrate upgrade
    mig_upgrade = migrate_sub.add_parser("upgrade", parents=[common], help="Upgrade database")
    mig_upgrade.add_argument("--to", default="head", help="Target revision (default: head)")
    mig_upgrade.add_argument("--yes", action="store_true", help="Confirm mutation")

    # db migrate downgrade
    mig_downgrade = migrate_sub.add_parser(
        "downgrade", parents=[common], help="Downgrade database"
    )
    mig_downgrade.add_argument("--to", required=True, help="Target revision")
    mig_downgrade.add_argument("--yes", action="store_true", help="Confirm mutation")

    # db migrate current
    migrate_sub.add_parser("current", parents=[common], help="Show current revision")

    # db migrate heads
    migrate_sub.add_parser("heads", parents=[common], help="Show head revisions")

    # db migrate stamp -> REMOVED

    # ---- users ----
    users_parser = subparsers.add_parser("users", help="User management")
    users_sub = users_parser.add_subparsers(dest="users_command")

    # users list
    users_list = users_sub.add_parser("list", parents=[common], help="List users")
    users_list.add_argument("--limit", type=int, default=50, help="Limit results")
    users_list.add_argument("--offset", type=int, default=0, help="Offset results")
    users_list.add_argument(
        "--include-disabled", action="store_true", help="Include disabled users"
    )

    # users show
    users_show = users_sub.add_parser("show", parents=[common], help="Show user details")
    _add_user_selector(users_show)

    # users set-role
    users_set_role = users_sub.add_parser("set-role", parents=[common], help="Set user role")
    _add_user_selector(users_set_role)
    users_set_role.add_argument(
        "--role", required=True, choices=["user", "admin"], help="Role to set"
    )
    users_set_role.add_argument("--yes", action="store_true", help="Confirm mutation")

    # users disable
    users_disable = users_sub.add_parser("disable", parents=[common], help="Disable user")
    _add_user_selector(users_disable)
    users_disable.add_argument("--yes", action="store_true", help="Confirm mutation")

    # users enable
    users_enable = users_sub.add_parser("enable", parents=[common], help="Enable user")
    _add_user_selector(users_enable)
    users_enable.add_argument("--yes", action="store_true", help="Confirm mutation")

    # users scopes
    users_scopes = users_sub.add_parser("scopes", help="Manage user scopes")
    scopes_sub = users_scopes.add_subparsers(dest="scopes_command")

    # users scopes add
    scopes_add = scopes_sub.add_parser("add", parents=[common], help="Add scopes")
    _add_user_selector(scopes_add)
    scopes_add.add_argument("--scope", action="append", required=True, help="Scope to add")
    scopes_add.add_argument("--yes", action="store_true", help="Confirm mutation")

    # users scopes remove
    scopes_remove = scopes_sub.add_parser("remove", parents=[common], help="Remove scopes")
    _add_user_selector(scopes_remove)
    scopes_remove.add_argument("--scope", action="append", required=True, help="Scope to remove")
    scopes_remove.add_argument("--yes", action="store_true", help="Confirm mutation")

    # users scopes set
    scopes_set = scopes_sub.add_parser("set", parents=[common], help="Set scopes (replace all)")
    _add_user_selector(scopes_set)
    scopes_set.add_argument("--scopes", required=True, help="Comma-separated scopes")
    scopes_set.add_argument("--yes", action="store_true", help="Confirm mutation")

    # ---- devices ----
    devices_parser = subparsers.add_parser("devices", help="Device management")
    devices_sub = devices_parser.add_subparsers(dest="devices_command")

    # devices list
    devices_list = devices_sub.add_parser("list", parents=[common], help="List devices for a user")
    _add_user_selector(devices_list)
    devices_list.add_argument(
        "--include-revoked", action="store_true", help="Include revoked devices"
    )

    # devices revoke
    devices_revoke = devices_sub.add_parser("revoke", parents=[common], help="Revoke a device")
    devices_revoke.add_argument("--device-id", required=True, help="Device ID (d...)")
    devices_revoke.add_argument("--yes", action="store_true", help="Confirm mutation")

    # ---- passkeys ----
    passkeys_parser = subparsers.add_parser("passkeys", help="Passkey management")
    passkeys_sub = passkeys_parser.add_subparsers(dest="passkeys_command")

    # passkeys list
    passkeys_list = passkeys_sub.add_parser(
        "list", parents=[common], help="List passkeys for a user"
    )
    _add_user_selector(passkeys_list)
    passkeys_list.add_argument(
        "--include-revoked", action="store_true", help="Include revoked passkeys"
    )

    # passkeys revoke
    passkeys_revoke = passkeys_sub.add_parser("revoke", parents=[common], help="Revoke a passkey")
    passkeys_revoke.add_argument("--key-id", required=True, help="Passkey ID (k...)")
    passkeys_revoke.add_argument("--yes", action="store_true", help="Confirm mutation")

    return parser


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------


def main() -> int:
    """CLI entry point. Returns an integer exit code."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return EXIT_BAD_ARGS

    # -- db --
    if args.command == "db":
        db_cmd = getattr(args, "db_command", None)
        if db_cmd == "ping":
            return _cmd_db_ping(args)
        # db init removed
        if db_cmd == "migrate":
            migrate_cmd = getattr(args, "migrate_command", None)
            if migrate_cmd == "upgrade":
                return _cmd_db_migrate_upgrade(args)
            if migrate_cmd == "downgrade":
                return _cmd_db_migrate_downgrade(args)
            if migrate_cmd == "current":
                return _cmd_db_migrate_current(args)
            if migrate_cmd == "heads":
                return _cmd_db_migrate_heads(args)
            # db migrate stamp removed
            parser.parse_args(["db", "migrate", "--help"])
            return EXIT_BAD_ARGS
        parser.parse_args(["db", "--help"])
        return EXIT_BAD_ARGS

    # -- users --
    if args.command == "users":
        users_cmd = getattr(args, "users_command", None)
        if users_cmd == "list":
            return _cmd_users_list(args)
        if users_cmd == "show":
            return _cmd_users_show(args)
        if users_cmd == "set-role":
            return _cmd_users_set_role(args)
        if users_cmd == "disable":
            return _cmd_users_disable(args)
        if users_cmd == "enable":
            return _cmd_users_enable(args)
        if users_cmd == "scopes":
            scopes_cmd = getattr(args, "scopes_command", None)
            if scopes_cmd == "add":
                return _cmd_users_scopes_add(args)
            if scopes_cmd == "remove":
                return _cmd_users_scopes_remove(args)
            if scopes_cmd == "set":
                return _cmd_users_scopes_set(args)
            parser.parse_args(["users", "scopes", "--help"])
            return EXIT_BAD_ARGS
        parser.parse_args(["users", "--help"])
        return EXIT_BAD_ARGS

    # -- devices --
    if args.command == "devices":
        devices_cmd = getattr(args, "devices_command", None)
        if devices_cmd == "list":
            return _cmd_devices_list(args)
        if devices_cmd == "revoke":
            return _cmd_devices_revoke(args)
        parser.parse_args(["devices", "--help"])
        return EXIT_BAD_ARGS

    # -- passkeys --
    if args.command == "passkeys":
        passkeys_cmd = getattr(args, "passkeys_command", None)
        if passkeys_cmd == "list":
            return _cmd_passkeys_list(args)
        if passkeys_cmd == "revoke":
            return _cmd_passkeys_revoke(args)
        parser.parse_args(["passkeys", "--help"])
        return EXIT_BAD_ARGS

    parser.print_help()
    return EXIT_BAD_ARGS
