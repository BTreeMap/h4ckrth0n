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


def missing_scopes(granted: Iterable[Scope], required: Iterable[Scope]) -> set[Scope]:
    """Return the required scopes that are not present in *granted*."""
    return set(required).difference(granted)


def add_scopes(existing: str | Iterable[str], to_add: str | Iterable[str]) -> str:
    """Add new scopes to an existing set of scopes, returning a serialized string."""
    return serialize_scopes((*parse_scopes(existing), *parse_scopes(to_add)))


def remove_scopes(existing: str | Iterable[str], to_remove: str | Iterable[str]) -> str:
    """Remove scopes from an existing set of scopes, returning a serialized string."""
    current = parse_scopes(existing)
    removing = set(parse_scopes(to_remove))
    return serialize_scopes(s for s in current if s not in removing)
