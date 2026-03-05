"""ReviewEngine orchestrator for mastiff."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from mastiff.analysis.prompt import PromptBuilder
from mastiff.core.models import ReviewResponse, ReviewResult
from mastiff.core.severity import SeverityJudge
from mastiff.diff.collector import collect_diff
from mastiff.diff.filter import filter_hunks
from mastiff.security.redactor import Redactor

if TYPE_CHECKING:
    from pathlib import Path

    from mastiff.config.schema import MastiffConfig
    from mastiff.core.provider import LLMProvider


class ReviewEngine:
    """Orchestrate the full review pipeline.

    Args:
        config: Mastiff configuration.
        provider: LLM provider satisfying the LLMProvider protocol.
    """

    def __init__(self, config: MastiffConfig, provider: LLMProvider) -> None:
        self.config = config
        self.provider = provider
        self.severity_judge = SeverityJudge(threshold=config.detection.score_threshold)
        self.redactor = Redactor()

    async def review(
        self,
        *,
        staged: bool = False,
        commit_range: str | None = None,
        cwd: Path | None = None,
        profile: str = "standard",
    ) -> ReviewResult:
        """Run a full code review pipeline.

        Args:
            staged: If True, review only staged changes.
            commit_range: If provided, diff between commits.
            cwd: Working directory for the git process.
            profile: Review profile (quick/standard/deep).

        Returns:
            ReviewResult with filtered findings and metadata.
        """
        # 1. Collect diff
        hunks = collect_diff(staged=staged, commit_range=commit_range, cwd=cwd)

        # 2. Filter hunks
        hunks = filter_hunks(
            hunks,
            exclude_patterns=self.config.context.exclude_patterns,
            never_send_paths=self.config.security.never_send_paths,
        )

        if not hunks:
            return ReviewResult(
                response=ReviewResponse(findings=[]),
                input_tokens=0,
                output_tokens=0,
                latency_ms=0.0,
                model=self.config.api.model,
                estimated_cost_usd=0.0,
            )

        # 3. Build diff text from hunks
        diff_parts: list[str] = []
        for h in hunks:
            parts: list[str] = [h.header]
            for _, line in h.added_lines:
                parts.append(f"+{line}")
            for _, line in h.removed_lines:
                parts.append(f"-{line}")
            diff_parts.append("\n".join(parts))
        diff_text = "\n".join(diff_parts)

        # 4. Redact secrets
        diff_text, _ = self.redactor.redact(diff_text)

        # 5. Build prompt
        builder = PromptBuilder(
            profile=profile,
            project_context=self.config.project.description or None,
        )
        prompt = builder.build(diff_text=diff_text, context_text="")

        # 6. Call LLM
        api_start = time.monotonic()
        response = await self.provider.review(prompt, model=self.config.api.model)
        api_ms = (time.monotonic() - api_start) * 1000

        # 7. Filter findings by severity
        filtered_findings = [
            f
            for f in response.findings
            if self.severity_judge.should_report(f.severity, confidence=f.confidence)
        ]

        return ReviewResult(
            response=ReviewResponse(findings=filtered_findings),
            input_tokens=0,
            output_tokens=0,
            latency_ms=api_ms,
            model=self.config.api.model,
            estimated_cost_usd=0.0,
        )
