"""Normalized response types for the LLM wrapper."""

from __future__ import annotations

from pydantic import BaseModel


class ChatResponse(BaseModel):
    """Minimal normalized response from an LLM chat call."""

    text: str
    model: str
    usage_prompt_tokens: int = 0
    usage_completion_tokens: int = 0
