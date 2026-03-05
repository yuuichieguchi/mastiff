"""LLM client for code review with cost guarding."""

from __future__ import annotations

import anthropic

from mastiff.analysis.prompt import PromptBuilder
from mastiff.analysis.response import parse_response
from mastiff.core.models import ReviewResponse


class CostGuard:
    """Enforce budget limits before making API calls.

    Args:
        max_cost_usd: Maximum allowed cost per run in USD.
        max_tokens: Maximum allowed tokens per run (None for unlimited).
    """

    def __init__(
        self,
        max_cost_usd: float = 1.0,
        max_tokens: int | None = None,
    ) -> None:
        self._max_cost_usd = max_cost_usd
        self._max_tokens = max_tokens

    def check(self, *, estimated_cost: float, tokens: int) -> bool:
        """Check whether a request is within budget.

        Args:
            estimated_cost: Estimated cost in USD.
            tokens: Estimated total tokens.

        Returns:
            True if within budget, False otherwise.
        """
        if estimated_cost > self._max_cost_usd:
            return False
        if self._max_tokens is not None and tokens > self._max_tokens:
            return False
        return True


class AnthropicProvider:
    """Anthropic API provider for code review.

    Args:
        api_key: Anthropic API key.
        model: Model identifier to use.
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model
        self._client = anthropic.Anthropic(api_key=api_key)

    @property
    def api_key(self) -> str:
        """The configured API key."""
        return self._api_key

    @property
    def model(self) -> str:
        """The configured model identifier."""
        return self._model

    async def review(
        self,
        *,
        diff_text: str,
        context_text: str,
        profile: str = "standard",
        project_context: str | None = None,
    ) -> ReviewResponse | None:
        """Run a code review via the Anthropic API.

        Args:
            diff_text: The unified diff to review.
            context_text: Surrounding context code.
            profile: Review profile (quick/standard/deep).
            project_context: Optional project description.

        Returns:
            Parsed ReviewResponse, or None if parsing fails.
        """
        builder = PromptBuilder(profile=profile, project_context=project_context)
        prompt = builder.build(diff_text=diff_text, context_text=context_text)

        message = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text
        return parse_response(response_text)
