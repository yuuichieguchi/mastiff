"""Prompt builder for LLM-based code review."""

from __future__ import annotations

from mastiff.analysis.categories import CATEGORY_DEFINITIONS

# Approximate characters per token (~4 chars/token for English code)
_CHARS_PER_TOKEN = 4

_PROFILE_LIMITS: dict[str, tuple[int, int]] = {
    "quick": (5000, 3000),
    "standard": (20000, 15000),
    "deep": (50000, 30000),
}

_SYSTEM_PROMPT = """\
You are a senior code reviewer specializing in detecting dangerous patterns \
in code changes. Your PRIORITY is to identify issues that could cause production \
incidents: blocking/deadlocks, race conditions, performance degradation, \
resource leaks, and security vulnerabilities.

Analyze the diff below and report findings in the specified JSON format. \
Only report issues you are confident about. Do not report style issues or \
minor improvements."""

_OUTPUT_SCHEMA = """\
Respond with a JSON object matching this schema:
{
  "schema_version": "1",
  "findings": [
    {
      "rule_id": "<category>-<short-name>",
      "category": "blocking|race_condition|degradation|resource_leak|security",
      "severity": "critical|warning|info",
      "file_path": "<path>",
      "line_start": <int>,
      "line_end": <int or null>,
      "title": "<short title>",
      "explanation": "<detailed explanation>",
      "suggested_fix": "<fix suggestion or null>",
      "confidence": <float 0.0-1.0>
    }
  ]
}

If no issues are found, return: {"schema_version": "1", "findings": []}"""


class PromptBuilder:
    """Build review prompts with profile-based token limits.

    Args:
        profile: One of "quick", "standard", or "deep".
        project_context: Optional project description to include.
    """

    def __init__(
        self,
        profile: str = "standard",
        project_context: str | None = None,
    ) -> None:
        if profile not in _PROFILE_LIMITS:
            raise ValueError(f"Unknown profile: {profile!r}")
        self._profile = profile
        self._project_context = project_context
        diff_limit, ctx_limit = _PROFILE_LIMITS[profile]
        self._max_diff_tokens = diff_limit
        self._max_context_tokens = ctx_limit

    @property
    def max_diff_tokens(self) -> int:
        """Maximum token budget for the diff section."""
        return self._max_diff_tokens

    @property
    def max_context_tokens(self) -> int:
        """Maximum token budget for the context section."""
        return self._max_context_tokens

    def build(self, *, diff_text: str, context_text: str) -> str:
        """Build the full review prompt.

        Args:
            diff_text: The unified diff text.
            context_text: Surrounding context code.

        Returns:
            The assembled prompt string.
        """
        parts: list[str] = []

        # System instruction
        parts.append(_SYSTEM_PROMPT)
        parts.append("")

        # Project context
        if self._project_context:
            parts.append(f"Project context: {self._project_context}")
            parts.append("")

        # Categories
        parts.append("Detection categories:")
        for key, cat in CATEGORY_DEFINITIONS.items():
            parts.append(f"- {cat['name']} ({key}): {cat['description']}")
        parts.append("")

        # Diff section (truncated)
        truncated_diff = self._truncate(diff_text, self._max_diff_tokens)
        parts.append("<diff>")
        parts.append(truncated_diff)
        parts.append("</diff>")
        parts.append("")

        # Context section (truncated)
        truncated_ctx = self._truncate(context_text, self._max_context_tokens)
        parts.append("<context>")
        parts.append(truncated_ctx)
        parts.append("</context>")
        parts.append("")

        # Output schema
        parts.append(_OUTPUT_SCHEMA)

        return "\n".join(parts)

    def _truncate(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within the token budget."""
        max_chars = max_tokens * _CHARS_PER_TOKEN
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n... [truncated]"
