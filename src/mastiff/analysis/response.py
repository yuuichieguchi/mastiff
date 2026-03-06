"""Response parser for LLM review output."""

from __future__ import annotations

import json
import logging
import re

from pydantic import ValidationError

from mastiff.core.models import ReviewResponse

logger = logging.getLogger(__name__)

_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n\s*```", re.DOTALL)


def parse_response(text: str) -> ReviewResponse | None:
    """Parse an LLM response text into a ReviewResponse model.

    Attempts three strategies in order:
    1. Direct JSON parse of the full text.
    2. Extract JSON from markdown code blocks (tries all blocks).
    3. Use ``json.JSONDecoder.raw_decode()`` to find embedded JSON objects.

    Returns None if parsing or validation fails.

    Args:
        text: Raw LLM response text.

    Returns:
        A validated ReviewResponse, or None on failure.
    """
    # 1. Try direct JSON parse
    data = _try_parse_json(text)
    if data is not None:
        result = _validate(data)
        if result is not None:
            return result
        logger.debug("Direct JSON parse succeeded but validation failed")

    # 2. Try extracting from markdown code blocks (all matches)
    for match in _CODE_BLOCK_RE.finditer(text):
        data = _try_parse_json(match.group(1))
        if data is not None:
            result = _validate(data)
            if result is not None:
                return result

    # 3. raw_decode() fallback — find embedded JSON objects in free text
    decoder = json.JSONDecoder()
    idx = 0
    candidates_tried = 0
    while idx < len(text):
        pos = text.find("{", idx)
        if pos == -1:
            break
        try:
            obj, end = decoder.raw_decode(text, pos)
            candidates_tried += 1
            if isinstance(obj, dict):
                result = _validate(obj)
                if result is not None:
                    return result
            idx = end
        except json.JSONDecodeError:
            idx = pos + 1

    logger.debug(
        "parse_response failed: tried %d JSON candidates from raw_decode, "
        "text length=%d, first 200 chars: %s",
        candidates_tried,
        len(text),
        text[:200],
    )
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
        response = ReviewResponse(**data)
    except (ValidationError, TypeError) as exc:
        logger.debug("ReviewResponse validation failed: %s", exc)
        return None

    # Log extra keys that were silently ignored
    known_keys = set(ReviewResponse.model_fields.keys())
    extra_keys = set(data.keys()) - known_keys
    if extra_keys:
        logger.warning("Ignored unexpected keys in LLM response: %s", extra_keys)

    return response
