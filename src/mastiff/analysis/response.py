"""Response parser for LLM review output."""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from mastiff.core.models import ReviewResponse

_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n\s*```", re.DOTALL)


def parse_response(text: str) -> ReviewResponse | None:
    """Parse an LLM response text into a ReviewResponse model.

    Attempts to parse the text as JSON directly. If that fails,
    tries to extract JSON from a markdown code block.

    Returns None if parsing or validation fails.

    Args:
        text: Raw LLM response text.

    Returns:
        A validated ReviewResponse, or None on failure.
    """
    # Try direct JSON parse
    data = _try_parse_json(text)
    if data is not None:
        return _validate(data)

    # Try extracting from markdown code block
    match = _CODE_BLOCK_RE.search(text)
    if match:
        data = _try_parse_json(match.group(1))
        if data is not None:
            return _validate(data)

    return None


def _try_parse_json(text: str) -> dict | None:  # type: ignore[type-arg]
    """Attempt to parse text as JSON, returning None on failure."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _validate(data: dict) -> ReviewResponse | None:  # type: ignore[type-arg]
    """Validate parsed JSON data against the ReviewResponse schema."""
    try:
        return ReviewResponse(**data)
    except (ValidationError, TypeError):
        return None
