"""Unit tests for the authz scopes value object and passkey error hierarchy."""

from __future__ import annotations

import pytest

from h4ckath0n.auth.authz import (
    ADMIN,
    USER,
    Scope,
    missing_scopes,
    parse_scopes,
    serialize_scopes,
)
from h4ckath0n.auth.passkeys.errors import (
    LastPasskeyError,
    PasskeyAlreadyRevokedError,
    PasskeyError,
    PasskeyNotFoundError,
    PasskeyRevokedError,
)


class TestScopes:
    def test_parse_trims_and_drops_empty(self):
        assert parse_scopes("  admin , demo ,, ") == [Scope("admin"), Scope("demo")]

    def test_parse_deduplicates_preserving_order(self):
        assert parse_scopes("a,b,a,c,b") == [Scope("a"), Scope("b"), Scope("c")]

    def test_parse_empty_string_yields_empty_list(self):
        assert parse_scopes("") == []
        assert parse_scopes("   ") == []

    def test_parse_scope_strings_from_an_iterable(self):
        assert parse_scopes(["admin,demo", "reports", "demo"]) == [
            Scope("admin"),
            Scope("demo"),
            Scope("reports"),
        ]

    def test_serialize_roundtrips(self):
        raw = "admin,demo,reports"
        assert serialize_scopes(parse_scopes(raw)) == raw

    def test_serialize_deduplicates(self):
        assert serialize_scopes([Scope("a"), Scope("a"), Scope("b")]) == "a,b"

    def test_missing_scopes_returns_difference(self):
        granted = parse_scopes("admin,demo")
        required = parse_scopes("admin,reports")
        assert missing_scopes(granted, required) == {Scope("reports")}

    def test_missing_scopes_empty_when_satisfied(self):
        granted = parse_scopes("admin,demo,reports")
        required = parse_scopes("admin,demo")
        assert missing_scopes(granted, required) == set()

    def test_normalize_scopes(self):
        from h4ckath0n.auth.authz import normalize_scopes

        assert normalize_scopes(" b , a ,, b, c ") == "b,a,c"

    def test_add_scopes(self):
        from h4ckath0n.auth.authz import add_scopes

        assert add_scopes("a,b", "b,c") == "a,b,c"

    def test_remove_scopes(self):
        from h4ckath0n.auth.authz import remove_scopes

        assert remove_scopes("a,b,c,d", "b,d,e") == "a,c"

    def test_role_constants(self):
        assert USER == "user"
        assert ADMIN == "admin"


class TestPasskeyErrors:
    def test_hierarchy_subclasses_value_error(self):
        for cls in (
            PasskeyNotFoundError,
            PasskeyAlreadyRevokedError,
            PasskeyRevokedError,
            LastPasskeyError,
        ):
            assert issubclass(cls, PasskeyError)
            assert issubclass(cls, ValueError)

    def test_default_messages_and_codes(self):
        assert PasskeyNotFoundError().code == "PASSKEY_NOT_FOUND"
        assert str(PasskeyNotFoundError()) == "Credential not found"
        assert PasskeyAlreadyRevokedError().code == "PASSKEY_ALREADY_REVOKED"
        assert PasskeyRevokedError().code == "PASSKEY_REVOKED"
        assert LastPasskeyError().code == "LAST_PASSKEY"

    def test_custom_message_overrides_default(self):
        err = PasskeyNotFoundError("nope")
        assert str(err) == "nope"
        assert err.code == "PASSKEY_NOT_FOUND"

    def test_raisable_and_catchable_as_value_error(self):
        with pytest.raises(ValueError, match="last active passkey"):
            raise LastPasskeyError()
