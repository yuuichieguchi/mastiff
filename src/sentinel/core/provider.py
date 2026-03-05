"""LLMProvider protocol for sentinel."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sentinel.core.models import ReviewResponse


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol that all LLM providers must satisfy."""

    async def review(self, prompt: str, model: str | None = None) -> ReviewResponse: ...
