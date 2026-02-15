"""Thin LLM client wrapper around the OpenAI SDK with safe defaults."""

from __future__ import annotations

import asyncio
import os

from openai import AsyncOpenAI, DefaultAioHttpClient, OpenAI

from h4ckath0n.llm.types import ChatResponse

# Default concurrency limit for outbound LLM calls.
_DEFAULT_CONCURRENCY = 10


class LLMClient:
    """Opinionated wrapper around the OpenAI SDK."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        resolved_key = (
            api_key
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("H4CKATH0N_OPENAI_API_KEY", "")
        )
        if not resolved_key:
            raise RuntimeError(
                "No OpenAI API key configured. Set OPENAI_API_KEY or H4CKATH0N_OPENAI_API_KEY."
            )
        self._client = OpenAI(
            api_key=resolved_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._model = model

    def chat(
        self,
        *,
        user: str,
        system: str = "You are a helpful assistant.",
        model: str | None = None,
    ) -> ChatResponse:
        """Send a chat completion and return a normalised :class:`ChatResponse`."""
        response = self._client.chat.completions.create(
            model=model or self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        choice = response.choices[0]
        usage = response.usage
        return ChatResponse(
            text=choice.message.content or "",
            model=response.model,
            usage_prompt_tokens=usage.prompt_tokens if usage else 0,
            usage_completion_tokens=usage.completion_tokens if usage else 0,
        )


class AsyncLLMClient:
    """Async wrapper around the OpenAI SDK using the aiohttp backend.

    Includes a concurrency limiter (``asyncio.Semaphore``) to avoid
    exhausting the provider rate limit or the DB connection pool under
    burst traffic.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        timeout: float = 30.0,
        max_retries: int = 2,
        max_concurrency: int = _DEFAULT_CONCURRENCY,
    ) -> None:
        resolved_key = (
            api_key
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("H4CKATH0N_OPENAI_API_KEY", "")
        )
        if not resolved_key:
            raise RuntimeError(
                "No OpenAI API key configured. Set OPENAI_API_KEY or H4CKATH0N_OPENAI_API_KEY."
            )
        self._client = AsyncOpenAI(
            api_key=resolved_key,
            http_client=DefaultAioHttpClient(),
            timeout=timeout,
            max_retries=max_retries,
        )
        self._model = model
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def chat(
        self,
        *,
        user: str,
        system: str = "You are a helpful assistant.",
        model: str | None = None,
    ) -> ChatResponse:
        """Send an async chat completion and return a normalised :class:`ChatResponse`."""
        async with self._semaphore:
            response = await self._client.chat.completions.create(
                model=model or self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        choice = response.choices[0]
        usage = response.usage
        return ChatResponse(
            text=choice.message.content or "",
            model=response.model,
            usage_prompt_tokens=usage.prompt_tokens if usage else 0,
            usage_completion_tokens=usage.completion_tokens if usage else 0,
        )


def llm(
    *,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
    timeout: float = 30.0,
    max_retries: int = 2,
) -> LLMClient:
    """Convenience factory. Equivalent to ``LLMClient(...)``."""
    return LLMClient(api_key=api_key, model=model, timeout=timeout, max_retries=max_retries)


def async_llm(
    *,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
    timeout: float = 30.0,
    max_retries: int = 2,
    max_concurrency: int = _DEFAULT_CONCURRENCY,
) -> AsyncLLMClient:
    """Convenience factory for the async client."""
    return AsyncLLMClient(
        api_key=api_key,
        model=model,
        timeout=timeout,
        max_retries=max_retries,
        max_concurrency=max_concurrency,
    )
