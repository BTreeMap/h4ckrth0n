"""h4ckath0n operator CLI.

Provides ``h4ckath0n`` console script and ``python -m h4ckath0n`` entry point.

This package is split into focused command modules; the public surface
(exit codes, ``main``, and helpers referenced by tests) is re-exported here
for backwards compatibility.
"""

from __future__ import annotations

import argparse

from h4ckath0n.auth.authz import normalize_scopes as _normalize_scopes
from h4ckath0n.cli._common import (
    EXIT_BAD_ARGS,
    EXIT_LAST_PASSKEY,
    EXIT_MIGRATIONS_MISSING,
    EXIT_NOT_FOUND,
    EXIT_OK,
    EXIT_PROD_INIT,
    _normalize_db_url_for_sync,
)
from h4ckath0n.cli._parser import build_parser
from h4ckath0n.cli.db import (
    _cmd_db_migrate_current,
    _cmd_db_migrate_downgrade,
    _cmd_db_migrate_heads,
    _cmd_db_migrate_upgrade,
    _cmd_db_ping,
    alembic_command,
)
from h4ckath0n.cli.devices import _cmd_devices_list, _cmd_devices_revoke
from h4ckath0n.cli.jobs import _cmd_jobs_worker
from h4ckath0n.cli.passkeys import _cmd_passkeys_list, _cmd_passkeys_revoke
from h4ckath0n.cli.seed import _cmd_seed_demo
from h4ckath0n.cli.users import (
    _cmd_users_disable,
    _cmd_users_enable,
    _cmd_users_list,
    _cmd_users_scopes_add,
    _cmd_users_scopes_remove,
    _cmd_users_scopes_set,
    _cmd_users_set_role,
    _cmd_users_show,
)

__all__ = [
    "EXIT_OK",
    "EXIT_NOT_FOUND",
    "EXIT_BAD_ARGS",
    "EXIT_LAST_PASSKEY",
    "EXIT_MIGRATIONS_MISSING",
    "EXIT_PROD_INIT",
    "main",
    "build_parser",
    "alembic_command",
    "_normalize_db_url_for_sync",
    "_normalize_scopes",
]

# Preserve historical parser alias.
_build_parser = build_parser


def _dispatch_db(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    db_cmd = getattr(args, "db_command", None)
    if db_cmd == "ping":
        return _cmd_db_ping(args)
    if db_cmd == "migrate":
        migrate_cmd = getattr(args, "migrate_command", "")
        handlers = {
            "upgrade": _cmd_db_migrate_upgrade,
            "downgrade": _cmd_db_migrate_downgrade,
            "current": _cmd_db_migrate_current,
            "heads": _cmd_db_migrate_heads,
        }
        if (handler := handlers.get(migrate_cmd)) is not None:
            return handler(args)
        parser.parse_args(["db", "migrate", "--help"])
        return EXIT_BAD_ARGS
    parser.parse_args(["db", "--help"])
    return EXIT_BAD_ARGS


def _dispatch_users(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    users_cmd = getattr(args, "users_command", "")
    handlers = {
        "list": _cmd_users_list,
        "show": _cmd_users_show,
        "set-role": _cmd_users_set_role,
        "disable": _cmd_users_disable,
        "enable": _cmd_users_enable,
    }
    if (handler := handlers.get(users_cmd)) is not None:
        return handler(args)
    if users_cmd == "scopes":
        scopes_cmd = getattr(args, "scopes_command", "")
        scope_handlers = {
            "add": _cmd_users_scopes_add,
            "remove": _cmd_users_scopes_remove,
            "set": _cmd_users_scopes_set,
        }
        if (handler := scope_handlers.get(scopes_cmd)) is not None:
            return handler(args)
        parser.parse_args(["users", "scopes", "--help"])
        return EXIT_BAD_ARGS
    parser.parse_args(["users", "--help"])
    return EXIT_BAD_ARGS


def _dispatch_devices(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    devices_cmd = getattr(args, "devices_command", "")
    if devices_cmd == "list":
        return _cmd_devices_list(args)
    if devices_cmd == "revoke":
        return _cmd_devices_revoke(args)
    parser.parse_args(["devices", "--help"])
    return EXIT_BAD_ARGS


def _dispatch_passkeys(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> int:
    passkeys_cmd = getattr(args, "passkeys_command", "")
    if passkeys_cmd == "list":
        return _cmd_passkeys_list(args)
    if passkeys_cmd == "revoke":
        return _cmd_passkeys_revoke(args)
    parser.parse_args(["passkeys", "--help"])
    return EXIT_BAD_ARGS


def _dispatch_jobs(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if getattr(args, "jobs_command", "") == "worker":
        return _cmd_jobs_worker(args)
    parser.parse_args(["jobs", "--help"])
    return EXIT_BAD_ARGS


def _dispatch_seed(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if getattr(args, "seed_command", "") == "demo":
        return _cmd_seed_demo(args)
    parser.parse_args(["seed", "--help"])
    return EXIT_BAD_ARGS


_DISPATCHERS = {
    "db": _dispatch_db,
    "users": _dispatch_users,
    "devices": _dispatch_devices,
    "passkeys": _dispatch_passkeys,
    "jobs": _dispatch_jobs,
    "seed": _dispatch_seed,
}


def main() -> int:
    """CLI entry point. Returns an integer exit code."""
    parser = build_parser()
    args = parser.parse_args()

    dispatch = _DISPATCHERS.get(args.command)
    if dispatch is None:
        parser.print_help()
        return EXIT_BAD_ARGS
    return dispatch(args, parser)
