"""Initialise observability middleware."""

from __future__ import annotations

import os
import uuid

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from h4ckath0n.obs.settings import ObservabilitySettings


class _TraceIdMiddleware(BaseHTTPMiddleware):
    """Attach a ``X-Trace-Id`` header to every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace_id = request.headers.get("x-trace-id", uuid.uuid4().hex)
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        return response


def init_observability(
    app: FastAPI,
    settings: ObservabilitySettings | None = None,
) -> None:
    """Wire up tracing middleware and configure LangSmith / OTEL env vars."""
    if settings is None:
        settings = ObservabilitySettings()

    app.add_middleware(_TraceIdMiddleware)

    if settings.langsmith_tracing:
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        if settings.langsmith_api_key:
            os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
        if settings.langsmith_project:
            os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
