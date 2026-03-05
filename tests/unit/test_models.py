"""Tests for mastiff.core.models — Pydantic data models."""
import pytest
from pydantic import ValidationError


class TestDetectionCategory:
    """DetectionCategory enum tests."""

    def test_has_all_categories(self):
        from mastiff.core.models import DetectionCategory
        assert hasattr(DetectionCategory, "BLOCKING")
        assert hasattr(DetectionCategory, "RACE_CONDITION")
        assert hasattr(DetectionCategory, "DEGRADATION")
        assert hasattr(DetectionCategory, "RESOURCE_LEAK")

    def test_category_values(self):
        from mastiff.core.models import DetectionCategory
        assert DetectionCategory.BLOCKING.value == "blocking"
        assert DetectionCategory.RACE_CONDITION.value == "race_condition"
        assert DetectionCategory.DEGRADATION.value == "degradation"
        assert DetectionCategory.RESOURCE_LEAK.value == "resource_leak"


class TestFindingSchema:
    """FindingSchema model tests."""

    def test_valid_finding(self):
        from mastiff.core.models import DetectionCategory, FindingSchema
        from mastiff.core.severity import Severity
        finding = FindingSchema(
            rule_id="blocking-sync-in-async",
            category=DetectionCategory.BLOCKING,
            severity=Severity.CRITICAL,
            file_path="src/main.py",
            line_start=42,
            line_end=45,
            title="Sync call in async context",
            explanation="time.sleep() blocks the event loop",
            confidence=0.9,
        )
        assert finding.rule_id == "blocking-sync-in-async"
        assert finding.schema_version == "1"
        assert finding.suggested_fix is None
        assert finding.column_start is None
        assert finding.symbol is None

    def test_finding_forbids_extra_fields(self):
        from mastiff.core.models import DetectionCategory, FindingSchema
        from mastiff.core.severity import Severity
        with pytest.raises(ValidationError):
            FindingSchema(
                rule_id="test",
                category=DetectionCategory.BLOCKING,
                severity=Severity.WARNING,
                file_path="x.py",
                line_start=1,
                title="t",
                explanation="e",
                confidence=0.5,
                unknown_field="bad",
            )

    def test_confidence_bounds(self):
        from mastiff.core.models import DetectionCategory, FindingSchema
        from mastiff.core.severity import Severity
        with pytest.raises(ValidationError):
            FindingSchema(
                rule_id="test",
                category=DetectionCategory.BLOCKING,
                severity=Severity.WARNING,
                file_path="x.py",
                line_start=1,
                title="t",
                explanation="e",
                confidence=1.5,  # > 1.0
            )
        with pytest.raises(ValidationError):
            FindingSchema(
                rule_id="test",
                category=DetectionCategory.BLOCKING,
                severity=Severity.WARNING,
                file_path="x.py",
                line_start=1,
                title="t",
                explanation="e",
                confidence=-0.1,  # < 0.0
            )

    def test_finding_with_all_optional_fields(self):
        from mastiff.core.models import DetectionCategory, FindingSchema
        from mastiff.core.severity import Severity
        finding = FindingSchema(
            rule_id="race-shared-state",
            category=DetectionCategory.RACE_CONDITION,
            severity=Severity.WARNING,
            file_path="src/worker.py",
            line_start=10,
            line_end=20,
            column_start=5,
            column_end=30,
            symbol="shared_counter",
            title="Unprotected shared state",
            explanation="shared_counter accessed without lock",
            suggested_fix="Use threading.Lock()",
            confidence=0.85,
        )
        assert finding.column_start == 5
        assert finding.column_end == 30
        assert finding.symbol == "shared_counter"
        assert finding.suggested_fix == "Use threading.Lock()"


class TestReviewResponse:
    """ReviewResponse model tests."""

    def test_empty_findings(self):
        from mastiff.core.models import ReviewResponse
        resp = ReviewResponse(findings=[])
        assert resp.findings == []
        assert resp.schema_version == "1"

    def test_response_forbids_extra_fields(self):
        from mastiff.core.models import ReviewResponse
        with pytest.raises(ValidationError):
            ReviewResponse(findings=[], extra="bad")

    def test_response_with_findings(self):
        from mastiff.core.models import DetectionCategory, FindingSchema, ReviewResponse
        from mastiff.core.severity import Severity
        finding = FindingSchema(
            rule_id="leak-file-handle",
            category=DetectionCategory.RESOURCE_LEAK,
            severity=Severity.WARNING,
            file_path="io.py",
            line_start=5,
            title="Unclosed file",
            explanation="File opened without context manager",
            confidence=0.7,
        )
        resp = ReviewResponse(findings=[finding])
        assert len(resp.findings) == 1
        assert resp.findings[0].rule_id == "leak-file-handle"


class TestDiffHunk:
    """DiffHunk model tests."""

    def test_diff_hunk_creation(self):
        from mastiff.core.models import DiffHunk
        hunk = DiffHunk(
            file_path="src/main.py",
            old_path=None,
            new_path="src/main.py",
            added_lines=[(10, "    x = 1")],
            removed_lines=[(10, "    x = 0")],
            context_lines=[(9, "def foo():"), (11, "    return x")],
            header="@@ -9,3 +9,3 @@ def foo():",
            is_rename=False,
            is_copy=False,
            is_binary=False,
        )
        assert hunk.file_path == "src/main.py"
        assert len(hunk.added_lines) == 1
        assert hunk.is_rename is False

    def test_diff_hunk_rename(self):
        from mastiff.core.models import DiffHunk
        hunk = DiffHunk(
            file_path="src/new.py",
            old_path="src/old.py",
            new_path="src/new.py",
            added_lines=[],
            removed_lines=[],
            context_lines=[],
            header="",
            is_rename=True,
            is_copy=False,
            is_binary=False,
        )
        assert hunk.is_rename is True
        assert hunk.old_path == "src/old.py"


class TestReviewResult:
    """ReviewResult model tests."""

    def test_review_result(self):
        from mastiff.core.models import ReviewResponse, ReviewResult
        result = ReviewResult(
            response=ReviewResponse(findings=[]),
            input_tokens=100,
            output_tokens=50,
            latency_ms=1200.5,
            model="claude-opus-4-20250514",
            estimated_cost_usd=0.05,
        )
        assert result.input_tokens == 100
        assert result.model == "claude-opus-4-20250514"
        assert result.estimated_cost_usd == 0.05
