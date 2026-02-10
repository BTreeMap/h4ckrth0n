"""Redaction utilities – strip secrets from trace payloads."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence

# Header names that must never appear in traces.
_SENSITIVE_HEADERS = frozenset(
    {
        "authorization",
        "x-api-key",
        "cookie",
        "set-cookie",
    }
)

# Patterns matched in values.
_SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+"),  # JWT-like
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI-style API key
    re.compile(r"lsv2_[A-Za-z0-9_]{20,}"),  # LangSmith key pattern
]


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return a copy of *headers* with sensitive entries masked."""
    out: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() in _SENSITIVE_HEADERS:
            out[k] = "[REDACTED]"
        else:
            out[k] = v
    return out


def redact_value(value: str) -> str:
    """Replace known secret patterns in *value* with ``[REDACTED]``."""
    result = value
    for pat in _SECRET_PATTERNS:
        result = pat.sub("[REDACTED]", result)
    return result


def make_redactor(
    extra_patterns: Sequence[re.Pattern[str]] | None = None,
) -> Callable[[str], str]:
    """Build a redactor function, optionally extending the default patterns."""
    patterns = list(_SECRET_PATTERNS)
    if extra_patterns:
        patterns.extend(extra_patterns)

    def _redact(value: str) -> str:
        result = value
        for pat in patterns:
            result = pat.sub("[REDACTED]", result)
        return result

    return _redact
