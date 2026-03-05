"""Severity enum and judgment matrix for sentinel findings."""

from __future__ import annotations

from enum import Enum


class Severity(Enum):
    """Severity levels for detected findings."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

    @property
    def weight(self) -> float:
        """Numeric weight for severity scoring."""
        weights: dict[Severity, float] = {
            Severity.CRITICAL: 1.0,
            Severity.WARNING: 0.7,
            Severity.INFO: 0.3,
        }
        return weights[self]


class SeverityJudge:
    """Two-axis severity × confidence judgment.

    Determines whether a finding should be reported based on
    the product of severity weight and confidence score.
    """

    def __init__(self, threshold: float = 0.5) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"threshold must be between 0.0 and 1.0, got {threshold}")
        self._threshold = threshold

    def score(self, severity: Severity, confidence: float) -> float:
        """Calculate the report score as severity.weight × confidence."""
        return severity.weight * confidence

    def should_report(self, severity: Severity, *, confidence: float) -> bool:
        """Return True if the score meets or exceeds the threshold."""
        return self.score(severity, confidence) >= self._threshold
