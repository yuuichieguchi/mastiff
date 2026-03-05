"""Redactor for stripping secrets from text before sending to external services."""

from __future__ import annotations

import math
from collections import Counter
from fnmatch import fnmatch
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from mastiff.security.patterns import SECRET_PATTERNS

if TYPE_CHECKING:
    import re

_REDACTED = "[REDACTED]"


class Redactor:
    """Detects and redacts secrets from text using regex patterns and entropy analysis.

    Args:
        patterns: Custom list of compiled regex patterns. Defaults to SECRET_PATTERNS.
        entropy_threshold: Shannon entropy threshold for high-entropy detection.
        min_entropy_length: Minimum string length to consider for entropy check.
    """

    def __init__(
        self,
        patterns: list[re.Pattern[str]] | None = None,
        entropy_threshold: float = 4.5,
        min_entropy_length: int = 20,
    ) -> None:
        self._patterns = patterns if patterns is not None else SECRET_PATTERNS
        self._entropy_threshold = entropy_threshold
        self._min_entropy_length = min_entropy_length

    def redact(self, text: str) -> tuple[str, int]:
        """Replace all detected secrets with [REDACTED].

        Returns:
            A tuple of (redacted_text, number_of_redactions).
        """
        count = 0
        result = text
        for pattern in self._patterns:
            result, n = pattern.subn(_REDACTED, result)
            count += n
        return result, count

    def is_high_entropy(self, s: str) -> bool:
        """Return True if the string has Shannon entropy above the threshold.

        Strings shorter than min_entropy_length are always considered low entropy
        to avoid false positives on short variable names, etc.
        """
        if len(s) < self._min_entropy_length:
            return False
        return self._shannon_entropy(s) >= self._entropy_threshold

    def should_exclude_path(self, path: str, never_send: list[str]) -> bool:
        """Return True if the path matches any of the never_send glob patterns.

        Checks both the full path and the basename against each pattern.
        """
        pure = PurePosixPath(path)
        for pattern in never_send:
            # Match against the full path
            if fnmatch(path, pattern):
                return True
            # Match against just the filename
            if fnmatch(pure.name, pattern):
                return True
            # Match each component path (for patterns like **/secrets/**)
            for i in range(len(pure.parts)):
                subpath = str(PurePosixPath(*pure.parts[i:]))
                if fnmatch(subpath, pattern):
                    return True
        return False

    @staticmethod
    def _shannon_entropy(s: str) -> float:
        """Calculate Shannon entropy of a string in bits."""
        if not s:
            return 0.0
        length = len(s)
        counts = Counter(s)
        entropy = 0.0
        for count in counts.values():
            probability = count / length
            if probability > 0:
                entropy -= probability * math.log2(probability)
        return entropy
