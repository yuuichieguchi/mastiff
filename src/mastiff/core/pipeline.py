"""ReviewPipeline abstract contract for mastiff."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mastiff.core.models import ReviewResult


class ReviewPipeline(abc.ABC):
    """Abstract base for review pipelines (CLI / LSP / pre-commit)."""

    @abc.abstractmethod
    async def run(self, diff_text: str, *, profile: str = "standard") -> ReviewResult: ...
