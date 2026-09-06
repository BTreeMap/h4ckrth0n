"""Passkey management subcommands."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from sqlalchemy import select

from h4ckath0n.auth.models import WebAuthnCredential
from h4ckath0n.cli._common import (
    EXIT_BAD_ARGS,
    EXIT_LAST_PASSKEY,
    EXIT_NOT_FOUND,
    EXIT_OK,
    _err,
    _output,
    _passkey_dict,
    _require_yes,
    _sync_session,
    _user_or_exit,
)

__all__ = ["_cmd_passkeys_list", "_cmd_passkeys_revoke"]


def _cmd_passkeys_list(args: argparse.Namespace) -> int:
    with _sync_session(args) as session:
        user, err = _user_or_exit(session, args)
        if err is not None:
            return err
        assert user is not None

        stmt = select(WebAuthnCredential).where(WebAuthnCredential.user_id == user.id)
        if not getattr(args, "include_revoked", False):
            stmt = stmt.where(WebAuthnCredential.revoked_at.is_(None))
        creds = session.execute(stmt).scalars().all()
        _output([_passkey_dict(c) for c in creds], fmt=args.format, pretty=args.pretty)
    return EXIT_OK


def _cmd_passkeys_revoke(args: argparse.Namespace) -> int:
    if not _require_yes(args):
        return EXIT_BAD_ARGS

    with _sync_session(args) as session:
        if (cred := session.get(WebAuthnCredential, args.key_id)) is None:
            _err("passkey not found")
            return EXIT_NOT_FOUND

        if cred.revoked_at is not None:
            _err("passkey already revoked")
            return EXIT_BAD_ARGS

        active_creds = (
            session.execute(
                select(WebAuthnCredential.id)
                .where(
                    WebAuthnCredential.user_id == cred.user_id,
                    WebAuthnCredential.revoked_at.is_(None),
                )
                .limit(2)
            )
            .scalars()
            .all()
        )

        if len(active_creds) <= 1:
            _err("refusing to revoke the last active passkey")
            return EXIT_LAST_PASSKEY

        cred.revoked_at = datetime.now(UTC)
        session.commit()
        session.refresh(cred)
        _output(_passkey_dict(cred), fmt=args.format, pretty=args.pretty)
    return EXIT_OK
