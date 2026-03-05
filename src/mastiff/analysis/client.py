"""LLM client for code review with cost guarding."""

from __future__ import annotations

import anthropic
from anthropic.types import TextBlock

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
        return not (self._max_tokens is not None and tokens > self._max_tokens)


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

    async def review(self, prompt: str, model: str | None = None) -> ReviewResponse:
        """Run a code review via the Anthropic API.

        Args:
            prompt: The fully-built review prompt.
            model: Optional model override (uses configured model if None).

        Returns:
            Parsed ReviewResponse (empty findings if parsing fails).
        """
        use_model = model or self._model

        message = self._client.messages.create(
            model=use_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        block = message.content[0]
        if not isinstance(block, TextBlock):
            return ReviewResponse(findings=[])
        response_text = block.text
        result = parse_response(response_text)
        return result if result is not None else ReviewResponse(findings=[])


class OpenAIProvider:
    """OpenAI API provider for code review."""

    def __init__(self, api_key: str, model: str) -> None:
        try:
            from openai import OpenAI as _OpenAI
        except ImportError:
            from mastiff.analysis.errors import MissingDependencyError

            msg = "Install mastiff[openai]: pip install 'mastiff[openai]'"
            raise MissingDependencyError(msg) from None
        self._api_key = api_key
        self._model = model
        self._client = _OpenAI(api_key=api_key)

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def model(self) -> str:
        return self._model

    async def review(self, prompt: str, model: str | None = None) -> ReviewResponse:
        use_model = model or self._model
        response = self._client.chat.completions.create(
            model=use_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            return ReviewResponse(findings=[])
        result = parse_response(content)
        return result if result is not None else ReviewResponse(findings=[])
