"""Authorization domain types: roles and scopes.

Roles and scopes were previously passed around as bare strings and parsed
ad-hoc from comma-separated values at several call sites.  This module
centralises that logic so the CSV representation lives in exactly one place
and authorization values carry intent in the type system.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, NewType

# Privilege tier stored as a short DB string.
Role = Literal["user", "admin"]

USER: Role = "user"
ADMIN: Role = "admin"

# Scopes stored comma-separated for compatibility.
Scope = NewType("Scope", str)


def parse_scopes(raw: str | Iterable[str]) -> list[Scope]:
    """Parse scope strings into an ordered, de-duplicated list.

    Each source string may contain comma-separated scopes. Whitespace is trimmed,
    empty entries are dropped, and insertion order is preserved.
    """
    source = (raw,) if isinstance(raw, str) else raw
    cleaned = (part.strip() for item in source for part in item.split(","))
    return [Scope(part) for part in dict.fromkeys(p for p in cleaned if p)]


def serialize_scopes(scopes: Iterable[Scope]) -> str:
    """Serialise scopes back into the canonical comma-separated form."""
    return ",".join(dict.fromkeys(str(s) for s in scopes if s))


def add_scopes(current: Iterable[Scope], to_add: Iterable[Scope]) -> list[Scope]:
    """Add new scopes to an existing set, preserving order and deduplicating."""
    return parse_scopes([*current, *to_add])


def remove_scopes(current: Iterable[Scope], to_remove: Iterable[Scope]) -> list[Scope]:
    """Remove scopes from an existing set, preserving order."""
    remove_set = set(to_remove)
    return [s for s in current if s not in remove_set]


def missing_scopes(granted: Iterable[Scope], required: Iterable[Scope]) -> set[Scope]:
    """Return the required scopes that are not present in *granted*."""
    return set(required).difference(granted)
