"""Tests for sentinel.core.severity — Severity enum and judgment matrix."""
import pytest


class TestSeverity:
    """Severity enum tests."""

    def test_severity_values(self):
        from sentinel.core.severity import Severity
        assert Severity.CRITICAL.value == "critical"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value == "info"

    def test_severity_weight(self):
        from sentinel.core.severity import Severity
        assert Severity.CRITICAL.weight == 1.0
        assert Severity.WARNING.weight == 0.7
        assert Severity.INFO.weight == 0.3

    def test_severity_ordering(self):
        from sentinel.core.severity import Severity
        # CRITICAL > WARNING > INFO
        assert Severity.CRITICAL.weight > Severity.WARNING.weight
        assert Severity.WARNING.weight > Severity.INFO.weight


class TestSeverityJudge:
    """SeverityJudge tests — severity × confidence 2-axis judgment."""

    def test_above_threshold_reports(self):
        from sentinel.core.severity import Severity, SeverityJudge
        judge = SeverityJudge(threshold=0.5)
        # warning(0.7) × confidence(0.8) = 0.56 → report
        assert judge.should_report(Severity.WARNING, confidence=0.8) is True

    def test_below_threshold_suppresses(self):
        from sentinel.core.severity import Severity, SeverityJudge
        judge = SeverityJudge(threshold=0.5)
        # info(0.3) × confidence(0.5) = 0.15 → suppress
        assert judge.should_report(Severity.INFO, confidence=0.5) is False

    def test_critical_always_reports_with_reasonable_confidence(self):
        from sentinel.core.severity import Severity, SeverityJudge
        judge = SeverityJudge(threshold=0.5)
        # critical(1.0) × confidence(0.6) = 0.6 → report
        assert judge.should_report(Severity.CRITICAL, confidence=0.6) is True

    def test_custom_threshold(self):
        from sentinel.core.severity import Severity, SeverityJudge
        judge = SeverityJudge(threshold=0.8)
        # warning(0.7) × confidence(0.9) = 0.63 → suppress with high threshold
        assert judge.should_report(Severity.WARNING, confidence=0.9) is False

    def test_score_calculation(self):
        from sentinel.core.severity import Severity, SeverityJudge
        judge = SeverityJudge(threshold=0.5)
        assert judge.score(Severity.WARNING, 0.8) == pytest.approx(0.56)
        assert judge.score(Severity.CRITICAL, 1.0) == pytest.approx(1.0)
        assert judge.score(Severity.INFO, 0.5) == pytest.approx(0.15)
