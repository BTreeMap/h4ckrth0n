"""User and scope management subcommands."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from sqlalchemy import func, select

from h4ckath0n.auth.authz import add_scopes, normalize_scopes, remove_scopes
from h4ckath0n.auth.models import Device, User, WebAuthnCredential
from h4ckath0n.cli._common import (
    EXIT_BAD_ARGS,
    EXIT_OK,
    _output,
    _require_yes,
    _sync_session,
    _user_dict,
    _user_or_exit,
)

__all__ = [
    "_cmd_users_list",
    "_cmd_users_show",
    "_cmd_users_set_role",
    "_cmd_users_disable",
    "_cmd_users_enable",
    "_cmd_users_scopes_add",
    "_cmd_users_scopes_remove",
    "_cmd_users_scopes_set",
]


def _cmd_users_list(args: argparse.Namespace) -> int:
    with _sync_session(args) as session:
        stmt = select(User)
        if not getattr(args, "include_disabled", False):
            stmt = stmt.where(User.disabled_at.is_(None))
        stmt = stmt.offset(args.offset).limit(args.limit)
        users = session.execute(stmt).scalars().all()
        _output([_user_dict(u) for u in users], fmt=args.format, pretty=args.pretty)
    return EXIT_OK


def _cmd_users_show(args: argparse.Namespace) -> int:
    with _sync_session(args) as session:
        user, err = _user_or_exit(session, args)
        if err is not None:
            return err
        assert user is not None

        devices_total = session.execute(
            select(func.count()).select_from(Device).where(Device.user_id == user.id)
        ).scalar()
        devices_active = session.execute(
            select(func.count())
            .select_from(Device)
            .where(Device.user_id == user.id, Device.revoked_at.is_(None))
        ).scalar()
        passkeys_total = session.execute(
            select(func.count())
            .select_from(WebAuthnCredential)
            .where(WebAuthnCredential.user_id == user.id)
        ).scalar()
        passkeys_active = session.execute(
            select(func.count())
            .select_from(WebAuthnCredential)
            .where(
                WebAuthnCredential.user_id == user.id,
                WebAuthnCredential.revoked_at.is_(None),
            )
        ).scalar()

        data = _user_dict(user)
        data["devices_total"] = devices_total or 0
        data["devices_active"] = devices_active or 0
        data["passkeys_total"] = passkeys_total or 0
        data["passkeys_active"] = passkeys_active or 0
        _output(data, fmt=args.format, pretty=args.pretty)
    return EXIT_OK


def _cmd_users_set_role(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    with _sync_session(args) as session:
        user, err = _user_or_exit(session, args)
        if err is not None:
            return err
        assert user is not None

        user.role = args.role
        session.commit()
        session.refresh(user)
        _output(_user_dict(user), fmt=args.format, pretty=args.pretty)
    return EXIT_OK


def _cmd_users_disable(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    with _sync_session(args) as session:
        user, err = _user_or_exit(session, args)
        if err is not None:
            return err
        assert user is not None

        user.disabled_at = datetime.now(UTC)
        session.commit()
        session.refresh(user)
        _output(_user_dict(user), fmt=args.format, pretty=args.pretty)
    return EXIT_OK


def _cmd_users_enable(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    with _sync_session(args) as session:
        user, err = _user_or_exit(session, args)
        if err is not None:
            return err
        assert user is not None

        user.disabled_at = None
        session.commit()
        session.refresh(user)
        _output(_user_dict(user), fmt=args.format, pretty=args.pretty)
    return EXIT_OK


def _cmd_users_scopes_add(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    with _sync_session(args) as session:
        user, err = _user_or_exit(session, args)
        if err is not None:
            return err
        assert user is not None

        user.scopes = add_scopes(user.scopes, args.scope)
        session.commit()
        session.refresh(user)
        _output(_user_dict(user), fmt=args.format, pretty=args.pretty)
    return EXIT_OK


def _cmd_users_scopes_remove(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    with _sync_session(args) as session:
        user, err = _user_or_exit(session, args)
        if err is not None:
            return err
        assert user is not None

        user.scopes = remove_scopes(user.scopes, args.scope)
        session.commit()
        session.refresh(user)
        _output(_user_dict(user), fmt=args.format, pretty=args.pretty)
    return EXIT_OK


def _cmd_users_scopes_set(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    with _sync_session(args) as session:
        user, err = _user_or_exit(session, args)
        if err is not None:
            return err
        assert user is not None

        user.scopes = normalize_scopes(args.scopes)
        session.commit()
        session.refresh(user)
        _output(_user_dict(user), fmt=args.format, pretty=args.pretty)
    return EXIT_OK
