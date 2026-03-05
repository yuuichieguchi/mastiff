"""Metrics collection for mastiff review runs."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ReviewMetrics:
    """Metrics for a single review run."""

    review_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    parse_failure_count: int = 0
    finding_count_by_category: dict[str, int] = field(default_factory=dict)
    model: str = ""
    profile: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, object]:
        """Convert metrics to a JSON-serializable dictionary."""
        return {k: v for k, v in self.__dict__.items()}


class MetricsCollector:
    """Append-only JSONL metrics collector.

    Args:
        metrics_file: Path to the JSONL file. Defaults to ~/.mastiff/metrics.jsonl.
    """

    def __init__(self, metrics_file: Path | None = None) -> None:
        self.metrics_file = metrics_file or Path.home() / ".mastiff" / "metrics.jsonl"

    def record(self, metrics: ReviewMetrics) -> None:
        """Append a metrics record to the JSONL file."""
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metrics_file, "a") as f:
            f.write(json.dumps(metrics.to_dict()) + "\n")

    def read_all(self) -> list[ReviewMetrics]:
        """Read all metrics records from the JSONL file."""
        if not self.metrics_file.exists():
            return []
        metrics: list[ReviewMetrics] = []
        for line in self.metrics_file.read_text().splitlines():
            if line.strip():
                data = json.loads(line)
                metrics.append(ReviewMetrics(**data))
        return metrics
