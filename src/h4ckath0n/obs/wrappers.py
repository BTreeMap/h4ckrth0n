"""Convenience wrappers for traced tools and graph nodes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from h4ckath0n.obs.redaction import redact_value


def traced_tool(
    fn: Callable[..., Any],
    *,
    name: str | None = None,
    redact: bool = False,
) -> Callable[..., Any]:
    """Wrap *fn* with metadata suitable for tracing frameworks.

    When *redact* is ``True``, string arguments and return values are passed
    through the default redactor before being recorded.
    """
    tool_name = name if name is not None else str(getattr(fn, "__name__", "tool"))

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if redact:
            kwargs = {k: redact_value(v) if isinstance(v, str) else v for k, v in kwargs.items()}
        result = fn(*args, **kwargs)
        wrapper.__trace_meta__ = {"tool_name": tool_name}  # type: ignore[attr-defined]
        return result

    wrapper.__name__ = tool_name  # type: ignore[attr-defined]
    wrapper.__trace_meta__ = {"tool_name": tool_name}  # type: ignore[attr-defined]
    return wrapper


def traced_node(
    fn: Callable[..., Any],
    *,
    name: str | None = None,
    metadata: dict[str, Any] | None = None,
    redact: bool = False,
) -> Callable[..., Any]:
    """Wrap *fn* with metadata suitable for LangGraph node tracing."""
    node_name = name if name is not None else str(getattr(fn, "__name__", "node"))
    meta = metadata or {}

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if redact:
            kwargs = {k: redact_value(v) if isinstance(v, str) else v for k, v in kwargs.items()}
        return fn(*args, **kwargs)

    wrapper.__name__ = node_name  # type: ignore[attr-defined]
    wrapper.__trace_meta__ = {"node_name": node_name, **meta}  # type: ignore[attr-defined]
    return wrapper
