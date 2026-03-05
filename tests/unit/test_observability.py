"""Tests for mastiff.observability — structured logging and metrics."""
import json
import logging


class TestGetLogger:
    """get_logger tests."""

    def test_returns_logger_with_mastiff_prefix(self):
        from mastiff.observability.logger import get_logger

        logger = get_logger("test")
        assert logger.name == "mastiff.test"

    def test_returns_logging_logger_instance(self):
        from mastiff.observability.logger import get_logger

        logger = get_logger("engine")
        assert isinstance(logger, logging.Logger)


class TestSetupLogging:
    """setup_logging tests."""

    def test_default_level_is_info(self):
        from mastiff.observability.logger import setup_logging

        setup_logging()
        logger = logging.getLogger("mastiff")
        assert logger.level == logging.INFO

    def test_verbose_sets_debug(self):
        from mastiff.observability.logger import setup_logging

        setup_logging(verbose=True)
        logger = logging.getLogger("mastiff")
        assert logger.level == logging.DEBUG

    def test_log_file_creates_file_handler(self, tmp_path):
        from mastiff.observability.logger import setup_logging

        log_file = tmp_path / "mastiff.log"
        # Clear existing handlers first
        logger = logging.getLogger("mastiff")
        logger.handlers.clear()

        setup_logging(log_file=log_file)
        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) >= 1

    def test_adds_stream_handler(self):
        from mastiff.observability.logger import setup_logging

        logger = logging.getLogger("mastiff")
        logger.handlers.clear()

        setup_logging()
        stream_handlers = [
            h for h in logger.handlers if isinstance(h, logging.StreamHandler)
        ]
        assert len(stream_handlers) >= 1


class TestReviewMetrics:
    """ReviewMetrics dataclass tests."""

    def test_default_values(self):
        from mastiff.observability.metrics import ReviewMetrics

        m = ReviewMetrics()
        assert m.review_latency_ms == 0.0
        assert m.total_latency_ms == 0.0
        assert m.input_tokens == 0
        assert m.output_tokens == 0
        assert m.estimated_cost_usd == 0.0
        assert m.parse_failure_count == 0
        assert m.finding_count_by_category == {}
        assert m.model == ""
        assert m.profile == ""
        assert isinstance(m.timestamp, float)

    def test_to_dict(self):
        from mastiff.observability.metrics import ReviewMetrics

        m = ReviewMetrics(
            review_latency_ms=100.0,
            input_tokens=500,
            model="claude-opus-4-20250514",
        )
        d = m.to_dict()
        assert d["review_latency_ms"] == 100.0
        assert d["input_tokens"] == 500
        assert d["model"] == "claude-opus-4-20250514"
        assert "timestamp" in d

    def test_custom_values(self):
        from mastiff.observability.metrics import ReviewMetrics

        m = ReviewMetrics(
            review_latency_ms=250.0,
            total_latency_ms=300.0,
            input_tokens=1000,
            output_tokens=200,
            estimated_cost_usd=0.05,
            parse_failure_count=1,
            finding_count_by_category={"blocking": 2, "race_condition": 1},
            model="test-model",
            profile="deep",
        )
        assert m.finding_count_by_category["blocking"] == 2
        assert m.profile == "deep"


class TestMetricsCollector:
    """MetricsCollector record/read tests."""

    def test_record_creates_file(self, tmp_path):
        from mastiff.observability.metrics import MetricsCollector, ReviewMetrics

        metrics_file = tmp_path / "metrics.jsonl"
        collector = MetricsCollector(metrics_file=metrics_file)
        collector.record(ReviewMetrics(model="test"))
        assert metrics_file.exists()

    def test_record_appends_json_line(self, tmp_path):
        from mastiff.observability.metrics import MetricsCollector, ReviewMetrics

        metrics_file = tmp_path / "metrics.jsonl"
        collector = MetricsCollector(metrics_file=metrics_file)
        collector.record(ReviewMetrics(model="first"))
        collector.record(ReviewMetrics(model="second"))
        lines = metrics_file.read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["model"] == "first"
        assert json.loads(lines[1])["model"] == "second"

    def test_read_all_returns_metrics(self, tmp_path):
        from mastiff.observability.metrics import MetricsCollector, ReviewMetrics

        metrics_file = tmp_path / "metrics.jsonl"
        collector = MetricsCollector(metrics_file=metrics_file)
        collector.record(ReviewMetrics(model="m1", input_tokens=100))
        collector.record(ReviewMetrics(model="m2", input_tokens=200))
        results = collector.read_all()
        assert len(results) == 2
        assert results[0].model == "m1"
        assert results[1].input_tokens == 200

    def test_read_all_empty_file(self, tmp_path):
        from mastiff.observability.metrics import MetricsCollector

        metrics_file = tmp_path / "metrics.jsonl"
        collector = MetricsCollector(metrics_file=metrics_file)
        results = collector.read_all()
        assert results == []

    def test_creates_parent_directories(self, tmp_path):
        from mastiff.observability.metrics import MetricsCollector, ReviewMetrics

        metrics_file = tmp_path / "sub" / "dir" / "metrics.jsonl"
        collector = MetricsCollector(metrics_file=metrics_file)
        collector.record(ReviewMetrics())
        assert metrics_file.exists()

    def test_default_metrics_file_path(self):
        from pathlib import Path

        from mastiff.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        assert collector.metrics_file == Path.home() / ".mastiff" / "metrics.jsonl"
