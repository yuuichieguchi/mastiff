"""ReviewPipeline abstract contract for sentinel."""

from __future__ import annotations

import abc

from sentinel.core.models import ReviewResult


class ReviewPipeline(abc.ABC):
    """Abstract base for review pipelines (CLI / LSP / pre-commit)."""

    @abc.abstractmethod
    async def run(self, diff_text: str, *, profile: str = "standard") -> ReviewResult: ...
