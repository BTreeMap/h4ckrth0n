"""SSE streaming helper built on ``sse-starlette``."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sse_starlette.sse import EventSourceResponse


def sse_response(
    event_generator: AsyncGenerator[dict[str, Any], None],
    **kwargs: Any,
) -> EventSourceResponse:
    """Wrap an async generator in an ``EventSourceResponse``.

    Each item yielded by *event_generator* should be a dict compatible
    with ``sse-starlette``'s ``ServerSentEvent`` (keys: ``event``,
    ``data``, ``id``, ``retry``, ``comment``).

    The generator should stop promptly when the client disconnects;
    ``sse-starlette`` handles cancellation internally.
    """
    return EventSourceResponse(event_generator, **kwargs)
