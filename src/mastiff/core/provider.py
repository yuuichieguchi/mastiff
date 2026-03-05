"""LLMProvider protocol for mastiff."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from mastiff.core.models import ReviewResponse


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol that all LLM providers must satisfy."""

    async def review(self, prompt: str, model: str | None = None) -> ReviewResponse: ...
