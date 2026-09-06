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


def add_scopes(existing_raw: str | Iterable[str], new_raw: str | Iterable[str]) -> str:
    """Combine and deduplicate existing and new scopes into a canonical string."""
    return serialize_scopes(parse_scopes(existing_raw) + parse_scopes(new_raw))


def remove_scopes(
    existing_raw: str | Iterable[str], remove_raw: str | Iterable[str]
) -> str:
    """Remove specific scopes from an existing set and return a canonical string."""
    existing = parse_scopes(existing_raw)
    to_remove = set(parse_scopes(remove_raw))
    return serialize_scopes(s for s in existing if s not in to_remove)
