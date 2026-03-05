"""Tests for mastiff.integrations — precommit and LSP."""
from __future__ import annotations

import asyncio

from mastiff.core.models import DetectionCategory, FindingSchema
from mastiff.core.severity import Severity


def _make_finding(
    line_start: int = 10,
    severity: Severity = Severity.WARNING,
) -> FindingSchema:
    return FindingSchema(
        rule_id="blocking-test",
        category=DetectionCategory.BLOCKING,
        severity=severity,
        file_path="src/main.py",
        line_start=line_start,
        line_end=line_start + 5,
        column_start=4,
        column_end=20,
        title="Blocking call detected",
        explanation="time.sleep() blocks the event loop",
        confidence=0.85,
    )


class TestFindingToDiagnostic:
    """Tests for finding_to_diagnostic conversion."""

    def test_converts_warning_finding(self):
        from mastiff.integrations.lsp.diagnostics import finding_to_diagnostic

        finding = _make_finding(severity=Severity.WARNING)
        diag = finding_to_diagnostic(finding)
        assert diag.source == "mastiff"
        assert "blocking-test" in diag.message
        assert "Blocking call detected" in diag.message

    def test_line_numbers_zero_indexed(self):
        from mastiff.integrations.lsp.diagnostics import finding_to_diagnostic

        finding = _make_finding(line_start=10)
        diag = finding_to_diagnostic(finding)
        # LSP uses 0-based line numbers; finding uses 1-based
        assert diag.range.start.line == 9
        assert diag.range.end.line == 14  # line_end=15 -> 14

    def test_severity_mapping_critical(self):
        from lsprotocol.types import DiagnosticSeverity

        from mastiff.integrations.lsp.diagnostics import finding_to_diagnostic

        finding = _make_finding(severity=Severity.CRITICAL)
        diag = finding_to_diagnostic(finding)
        assert diag.severity == DiagnosticSeverity.Error

    def test_severity_mapping_warning(self):
        from lsprotocol.types import DiagnosticSeverity

        from mastiff.integrations.lsp.diagnostics import finding_to_diagnostic

        finding = _make_finding(severity=Severity.WARNING)
        diag = finding_to_diagnostic(finding)
        assert diag.severity == DiagnosticSeverity.Warning

    def test_severity_mapping_info(self):
        from lsprotocol.types import DiagnosticSeverity

        from mastiff.integrations.lsp.diagnostics import finding_to_diagnostic

        finding = _make_finding(severity=Severity.INFO)
        diag = finding_to_diagnostic(finding)
        assert diag.severity == DiagnosticSeverity.Information

    def test_column_positions(self):
        from mastiff.integrations.lsp.diagnostics import finding_to_diagnostic

        finding = _make_finding()
        diag = finding_to_diagnostic(finding)
        assert diag.range.start.character == 4
        assert diag.range.end.character == 20


class TestDebouncer:
    """Tests for Debouncer cancellation logic."""

    async def test_debounce_executes_callback(self):
        from mastiff.integrations.lsp.debounce import Debouncer

        result: list[str] = []

        async def callback(value: str) -> None:
            result.append(value)

        debouncer = Debouncer(delay_ms=50)
        debouncer.debounce("key1", callback, "hello")
        await asyncio.sleep(0.1)
        assert result == ["hello"]

    async def test_debounce_cancels_previous(self):
        from mastiff.integrations.lsp.debounce import Debouncer

        result: list[str] = []

        async def callback(value: str) -> None:
            result.append(value)

        debouncer = Debouncer(delay_ms=100)
        debouncer.debounce("key1", callback, "first")
        await asyncio.sleep(0.01)  # short wait, before first fires
        debouncer.debounce("key1", callback, "second")
        await asyncio.sleep(0.2)
        # Only the second should have fired
        assert result == ["second"]

    async def test_debounce_different_keys_independent(self):
        from mastiff.integrations.lsp.debounce import Debouncer

        result: list[str] = []

        async def callback(value: str) -> None:
            result.append(value)

        debouncer = Debouncer(delay_ms=50)
        debouncer.debounce("key1", callback, "a")
        debouncer.debounce("key2", callback, "b")
        await asyncio.sleep(0.1)
        assert sorted(result) == ["a", "b"]

    async def test_cancel_removes_pending(self):
        from mastiff.integrations.lsp.debounce import Debouncer

        result: list[str] = []

        async def callback(value: str) -> None:
            result.append(value)

        debouncer = Debouncer(delay_ms=100)
        debouncer.debounce("key1", callback, "hello")
        debouncer.cancel("key1")
        await asyncio.sleep(0.2)
        assert result == []


class TestReviewScheduler:
    """Tests for ReviewScheduler caching and concurrency."""

    def test_cache_stores_and_retrieves(self):
        from mastiff.integrations.lsp.scheduler import ReviewScheduler

        scheduler = ReviewScheduler()
        scheduler.cache_result("file.py", "abc123", {"findings": []})
        result = scheduler.get_cached("file.py", "abc123")
        assert result == {"findings": []}

    def test_cache_miss_returns_none(self):
        from mastiff.integrations.lsp.scheduler import ReviewScheduler

        scheduler = ReviewScheduler()
        result = scheduler.get_cached("file.py", "abc123")
        assert result is None

    def test_lru_eviction(self):
        from mastiff.integrations.lsp.scheduler import ReviewScheduler

        scheduler = ReviewScheduler(cache_max=3)
        scheduler.cache_result("a.py", "h1", "result_a")
        scheduler.cache_result("b.py", "h2", "result_b")
        scheduler.cache_result("c.py", "h3", "result_c")
        # Cache is full (3 items). Add one more to trigger eviction.
        scheduler.cache_result("d.py", "h4", "result_d")
        # Oldest (a.py:h1) should be evicted
        assert scheduler.get_cached("a.py", "h1") is None
        assert scheduler.get_cached("b.py", "h2") == "result_b"
        assert scheduler.get_cached("d.py", "h4") == "result_d"

    def test_lru_access_updates_order(self):
        from mastiff.integrations.lsp.scheduler import ReviewScheduler

        scheduler = ReviewScheduler(cache_max=3)
        scheduler.cache_result("a.py", "h1", "result_a")
        scheduler.cache_result("b.py", "h2", "result_b")
        scheduler.cache_result("c.py", "h3", "result_c")
        # Access a.py to make it most recently used
        scheduler.get_cached("a.py", "h1")
        # Add new item; b.py (least recently used) should be evicted
        scheduler.cache_result("d.py", "h4", "result_d")
        assert scheduler.get_cached("a.py", "h1") == "result_a"
        assert scheduler.get_cached("b.py", "h2") is None

    def test_diff_hash_deterministic(self):
        from mastiff.integrations.lsp.scheduler import ReviewScheduler

        scheduler = ReviewScheduler()
        h1 = scheduler.diff_hash("hello world")
        h2 = scheduler.diff_hash("hello world")
        assert h1 == h2

    def test_diff_hash_different_content(self):
        from mastiff.integrations.lsp.scheduler import ReviewScheduler

        scheduler = ReviewScheduler()
        h1 = scheduler.diff_hash("hello")
        h2 = scheduler.diff_hash("world")
        assert h1 != h2

    async def test_semaphore_limits_concurrency(self):
        from mastiff.integrations.lsp.scheduler import ReviewScheduler

        scheduler = ReviewScheduler(max_concurrent=2)
        active: list[int] = []
        max_active = [0]

        async def task(idx: int) -> int:
            active.append(idx)
            if len(active) > max_active[0]:
                max_active[0] = len(active)
            await asyncio.sleep(0.05)
            active.remove(idx)
            return idx

        results = await asyncio.gather(
            scheduler.run(task(1)),
            scheduler.run(task(2)),
            scheduler.run(task(3)),
            scheduler.run(task(4)),
        )
        assert sorted(results) == [1, 2, 3, 4]
        assert max_active[0] <= 2
