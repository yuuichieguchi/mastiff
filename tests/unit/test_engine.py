"""Tests for mastiff.core.engine — ReviewEngine orchestrator."""
from __future__ import annotations

from unittest.mock import patch

from mastiff.config.schema import MastiffConfig
from mastiff.core.models import (
    DetectionCategory,
    DiffHunk,
    FindingSchema,
    ReviewResponse,
    ReviewResult,
)
from mastiff.core.severity import Severity


class FakeLLMProvider:
    """Fake LLM provider for testing."""

    def __init__(self, response: ReviewResponse | None = None) -> None:
        self._response = response or ReviewResponse(findings=[])
        self.calls: list[tuple[str, str | None]] = []

    async def review(self, prompt: str, model: str | None = None) -> ReviewResponse:
        self.calls.append((prompt, model))
        return self._response


def _make_hunk(
    file_path: str = "src/main.py",
    added: list[tuple[int, str]] | None = None,
    removed: list[tuple[int, str]] | None = None,
) -> DiffHunk:
    return DiffHunk(
        file_path=file_path,
        old_path=None,
        new_path=file_path,
        added_lines=added or [(1, "x = 1")],
        removed_lines=removed or [],
        context_lines=[],
        header="@@ -1,1 +1,1 @@",
    )


def _make_finding(
    severity: Severity = Severity.CRITICAL,
    confidence: float = 0.9,
    rule_id: str = "blocking-test",
    category: DetectionCategory = DetectionCategory.BLOCKING,
) -> FindingSchema:
    return FindingSchema(
        rule_id=rule_id,
        category=category,
        severity=severity,
        file_path="src/main.py",
        line_start=1,
        title="Test finding",
        explanation="Test explanation",
        confidence=confidence,
    )


class TestReviewEngineEmptyDiff:
    """Tests for empty diff scenarios."""

    async def test_empty_diff_returns_empty_findings(self):
        from mastiff.core.engine import ReviewEngine

        config = MastiffConfig()
        provider = FakeLLMProvider()
        engine = ReviewEngine(config=config, provider=provider)

        with patch("mastiff.core.engine.collect_diff", return_value=[]):
            result = await engine.review(staged=True)

        assert isinstance(result, ReviewResult)
        assert result.response.findings == []
        assert len(provider.calls) == 0

    async def test_empty_diff_returns_zero_tokens(self):
        from mastiff.core.engine import ReviewEngine

        config = MastiffConfig()
        provider = FakeLLMProvider()
        engine = ReviewEngine(config=config, provider=provider)

        with patch("mastiff.core.engine.collect_diff", return_value=[]):
            result = await engine.review(staged=True)

        assert result.input_tokens == 0
        assert result.output_tokens == 0


class TestReviewEngineSeverityFiltering:
    """Tests for severity-based filtering."""

    async def test_findings_below_threshold_filtered(self):
        from mastiff.core.engine import ReviewEngine

        # INFO (0.3) × 0.5 = 0.15 → below default threshold 0.5
        low_finding = _make_finding(severity=Severity.INFO, confidence=0.5)
        response = ReviewResponse(findings=[low_finding])
        provider = FakeLLMProvider(response=response)
        config = MastiffConfig()
        engine = ReviewEngine(config=config, provider=provider)

        hunks = [_make_hunk()]
        with patch("mastiff.core.engine.collect_diff", return_value=hunks):
            result = await engine.review(staged=True)

        assert len(result.response.findings) == 0

    async def test_findings_above_threshold_kept(self):
        from mastiff.core.engine import ReviewEngine

        # CRITICAL (1.0) × 0.9 = 0.9 → above default threshold 0.5
        high_finding = _make_finding(severity=Severity.CRITICAL, confidence=0.9)
        response = ReviewResponse(findings=[high_finding])
        provider = FakeLLMProvider(response=response)
        config = MastiffConfig()
        engine = ReviewEngine(config=config, provider=provider)

        hunks = [_make_hunk()]
        with patch("mastiff.core.engine.collect_diff", return_value=hunks):
            result = await engine.review(staged=True)

        assert len(result.response.findings) == 1
        assert result.response.findings[0].rule_id == "blocking-test"

    async def test_mixed_findings_partially_filtered(self):
        from mastiff.core.engine import ReviewEngine

        findings = [
            _make_finding(severity=Severity.CRITICAL, confidence=0.9, rule_id="keep-me"),
            _make_finding(severity=Severity.INFO, confidence=0.3, rule_id="drop-me"),
        ]
        response = ReviewResponse(findings=findings)
        provider = FakeLLMProvider(response=response)
        config = MastiffConfig()
        engine = ReviewEngine(config=config, provider=provider)

        hunks = [_make_hunk()]
        with patch("mastiff.core.engine.collect_diff", return_value=hunks):
            result = await engine.review(staged=True)

        assert len(result.response.findings) == 1
        assert result.response.findings[0].rule_id == "keep-me"


class TestReviewEngineProviderCalls:
    """Tests for LLM provider interaction."""

    async def test_engine_calls_provider_with_model(self):
        from mastiff.core.engine import ReviewEngine

        provider = FakeLLMProvider()
        config = MastiffConfig()
        engine = ReviewEngine(config=config, provider=provider)

        hunks = [_make_hunk()]
        with patch("mastiff.core.engine.collect_diff", return_value=hunks):
            await engine.review(staged=True)

        assert len(provider.calls) == 1
        _, model = provider.calls[0]
        assert model == config.api.model

    async def test_engine_passes_prompt_string(self):
        from mastiff.core.engine import ReviewEngine

        provider = FakeLLMProvider()
        config = MastiffConfig()
        engine = ReviewEngine(config=config, provider=provider)

        hunks = [_make_hunk()]
        with patch("mastiff.core.engine.collect_diff", return_value=hunks):
            await engine.review(staged=True)

        prompt, _ = provider.calls[0]
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    async def test_result_contains_model_name(self):
        from mastiff.core.engine import ReviewEngine

        provider = FakeLLMProvider()
        config = MastiffConfig()
        engine = ReviewEngine(config=config, provider=provider)

        hunks = [_make_hunk()]
        with patch("mastiff.core.engine.collect_diff", return_value=hunks):
            result = await engine.review(staged=True)

        assert result.model == config.api.model

    async def test_result_has_latency(self):
        from mastiff.core.engine import ReviewEngine

        provider = FakeLLMProvider()
        config = MastiffConfig()
        engine = ReviewEngine(config=config, provider=provider)

        hunks = [_make_hunk()]
        with patch("mastiff.core.engine.collect_diff", return_value=hunks):
            result = await engine.review(staged=True)

        assert result.latency_ms >= 0.0


class TestReviewEngineModelOverride:
    """Tests for model override behavior with different provider types."""

    async def test_api_provider_receives_model_override(self):
        """API providers should receive model=config.api.model."""
        from mastiff.core.engine import ReviewEngine

        provider = FakeLLMProvider()
        provider.supports_runtime_model_override = True
        config = MastiffConfig()
        engine = ReviewEngine(config=config, provider=provider)

        hunks = [_make_hunk()]
        with patch("mastiff.core.engine.collect_diff", return_value=hunks):
            await engine.review(staged=True)

        _, model = provider.calls[0]
        assert model == config.api.model

    async def test_cli_provider_does_not_receive_model_override(self):
        """CLI providers (supports_runtime_model_override=False) should receive model=None."""
        from mastiff.core.engine import ReviewEngine

        provider = FakeLLMProvider()
        provider.supports_runtime_model_override = False
        config = MastiffConfig()
        engine = ReviewEngine(config=config, provider=provider)

        hunks = [_make_hunk()]
        with patch("mastiff.core.engine.collect_diff", return_value=hunks):
            await engine.review(staged=True)

        _, model = provider.calls[0]
        assert model is None


class TestReviewEngineFilteredHunks:
    """Tests for hunk filtering (exclude patterns, never_send_paths)."""

    async def test_all_hunks_filtered_returns_empty(self):
        from mastiff.core.engine import ReviewEngine

        provider = FakeLLMProvider()
        config = MastiffConfig()
        engine = ReviewEngine(config=config, provider=provider)

        hunks = [_make_hunk(file_path="node_modules/pkg/index.js")]
        with patch("mastiff.core.engine.collect_diff", return_value=hunks):
            result = await engine.review(staged=True)

        assert result.response.findings == []
        assert len(provider.calls) == 0
