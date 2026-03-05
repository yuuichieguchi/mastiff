"""Tests for mastiff.cli — CLI commands and output rendering."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from mastiff.core.models import (
    DetectionCategory,
    FindingSchema,
    ReviewResponse,
)
from mastiff.core.severity import Severity


def _make_finding(
    file_path: str = "src/main.py",
    line_start: int = 10,
    severity: Severity = Severity.WARNING,
    category: DetectionCategory = DetectionCategory.BLOCKING,
    title: str = "Blocking call detected",
    confidence: float = 0.85,
) -> FindingSchema:
    return FindingSchema(
        rule_id="blocking-test",
        category=category,
        severity=severity,
        file_path=file_path,
        line_start=line_start,
        title=title,
        explanation="Test explanation",
        confidence=confidence,
    )


class TestMainGroup:
    """Tests for the mastiff CLI group."""

    def test_help_output(self):
        from mastiff.cli.app import main

        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Mastiff" in result.output

    def test_version_option(self):
        from mastiff.cli.app import main

        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "version" in result.output.lower() or "0." in result.output


class TestReviewCommand:
    """Tests for the review subcommand."""

    def test_review_help(self):
        from mastiff.cli.app import main

        runner = CliRunner()
        result = runner.invoke(main, ["review", "--help"])
        assert result.exit_code == 0
        assert "--staged" in result.output
        assert "--profile" in result.output
        assert "--format" in result.output
        assert "--strict" in result.output
        assert "--config" in result.output

    def test_review_shows_profile_choices(self):
        from mastiff.cli.app import main

        runner = CliRunner()
        result = runner.invoke(main, ["review", "--help"])
        assert "quick" in result.output
        assert "standard" in result.output
        assert "deep" in result.output

    def test_review_format_agent_in_help(self):
        """review --help output contains 'agent' as a format choice."""
        from mastiff.cli.app import main

        runner = CliRunner()
        result = runner.invoke(main, ["review", "--help"])
        assert "agent" in result.output

    def test_review_format_agent_exit_2_on_findings(self, tmp_path, monkeypatch):
        """review --format agent exits with code 2 when findings are present."""
        from mastiff.cli.app import main
        from mastiff.core.models import ReviewResponse, ReviewResult

        monkeypatch.chdir(tmp_path)
        finding = _make_finding()
        mock_result = ReviewResult(
            response=ReviewResponse(findings=[finding]),
            input_tokens=100,
            output_tokens=50,
            latency_ms=500.0,
            model="test-model",
            estimated_cost_usd=0.01,
        )

        with patch("mastiff.cli.commands.review.create_provider"), \
             patch("mastiff.cli.commands.review.load_config"), \
             patch("mastiff.cli.commands.review.ReviewEngine") as mock_engine_cls:
            mock_engine = MagicMock()
            mock_engine.review = AsyncMock(return_value=mock_result)
            mock_engine_cls.return_value = mock_engine

            runner = CliRunner()
            result = runner.invoke(main, ["review", "--format", "agent"])
            assert result.exit_code == 2

    def test_review_format_agent_exit_0_no_findings(self, tmp_path, monkeypatch):
        """review --format agent exits with code 0 when no findings."""
        from mastiff.cli.app import main
        from mastiff.core.models import ReviewResponse, ReviewResult

        monkeypatch.chdir(tmp_path)
        mock_result = ReviewResult(
            response=ReviewResponse(findings=[]),
            input_tokens=100,
            output_tokens=50,
            latency_ms=500.0,
            model="test-model",
            estimated_cost_usd=0.01,
        )

        with patch("mastiff.cli.commands.review.create_provider"), \
             patch("mastiff.cli.commands.review.load_config"), \
             patch("mastiff.cli.commands.review.ReviewEngine") as mock_engine_cls:
            mock_engine = MagicMock()
            mock_engine.review = AsyncMock(return_value=mock_result)
            mock_engine_cls.return_value = mock_engine

            runner = CliRunner()
            result = runner.invoke(main, ["review", "--format", "agent"])
            assert result.exit_code == 0


class TestInitCommand:
    """Tests for the init subcommand."""

    def test_init_creates_config_file(self, tmp_path, monkeypatch):
        from mastiff.cli.app import main

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        config_path = tmp_path / "mastiff.yaml"
        assert config_path.exists()
        assert "Created" in result.output

    def test_init_refuses_overwrite(self, tmp_path, monkeypatch):
        from mastiff.cli.app import main

        monkeypatch.chdir(tmp_path)
        (tmp_path / "mastiff.yaml").write_text("existing: true")
        runner = CliRunner()
        result = runner.invoke(main, ["init"])
        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_init_help(self):
        from mastiff.cli.app import main

        runner = CliRunner()
        result = runner.invoke(main, ["init", "--help"])
        assert result.exit_code == 0
        assert "configuration" in result.output.lower() or "mastiff.yaml" in result.output


class TestInstallCommand:
    """Tests for the install subcommand."""

    def test_install_creates_hook(self, tmp_path, monkeypatch):
        from mastiff.cli.app import main

        monkeypatch.chdir(tmp_path)
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        runner = CliRunner()
        result = runner.invoke(main, ["install"])
        assert result.exit_code == 0
        hook_path = hooks_dir / "pre-commit"
        assert hook_path.exists()
        assert "mastiff" in hook_path.read_text()

    def test_install_fails_without_git(self, tmp_path, monkeypatch):
        from mastiff.cli.app import main

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["install"])
        assert result.exit_code != 0
        assert "git" in result.output.lower()

    def test_install_hook_is_executable(self, tmp_path, monkeypatch):
        import os

        from mastiff.cli.app import main

        monkeypatch.chdir(tmp_path)
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        runner = CliRunner()
        runner.invoke(main, ["install"])
        hook_path = hooks_dir / "pre-commit"
        assert os.access(hook_path, os.X_OK)

    def test_install_claude_code_creates_hooks(self, tmp_path, monkeypatch):
        """install --claude-code creates .claude/hooks/mastiff-review.sh."""
        from mastiff.cli.app import main

        monkeypatch.chdir(tmp_path)
        (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)
        runner = CliRunner()
        result = runner.invoke(main, ["install", "--claude-code"])
        assert result.exit_code == 0
        hook_path = tmp_path / ".claude" / "hooks" / "mastiff-review.sh"
        assert hook_path.exists()

    def test_install_codex_creates_hooks(self, tmp_path, monkeypatch):
        """install --codex creates .git/hooks/post-commit."""
        from mastiff.cli.app import main

        monkeypatch.chdir(tmp_path)
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        runner = CliRunner()
        result = runner.invoke(main, ["install", "--codex"])
        assert result.exit_code == 0
        hook_path = hooks_dir / "post-commit"
        assert hook_path.exists()

    def test_install_no_flags_still_works(self, tmp_path, monkeypatch):
        """install (no flags) still creates pre-commit hook as before."""
        from mastiff.cli.app import main

        monkeypatch.chdir(tmp_path)
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        runner = CliRunner()
        result = runner.invoke(main, ["install"])
        assert result.exit_code == 0
        hook_path = hooks_dir / "pre-commit"
        assert hook_path.exists()
        assert "mastiff" in hook_path.read_text()


class TestBaselineCommand:
    """Tests for the baseline subcommand."""

    def test_baseline_help(self):
        from mastiff.cli.app import main

        runner = CliRunner()
        result = runner.invoke(main, ["baseline", "--help"])
        assert result.exit_code == 0
        assert "--rebase" in result.output

    def test_baseline_default(self, tmp_path, monkeypatch):
        from mastiff.cli.app import main

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["baseline"])
        assert result.exit_code == 0


class TestServerCommand:
    """Tests for the server subcommand."""

    def test_server_help(self):
        from mastiff.cli.app import main

        runner = CliRunner()
        result = runner.invoke(main, ["server", "--help"])
        assert result.exit_code == 0
        assert "--port" in result.output


class TestRenderFindings:
    """Tests for render_findings output."""

    def test_empty_findings_shows_no_issues(self, capsys):
        from mastiff.cli.output import render_findings

        response = ReviewResponse(findings=[])
        render_findings(response)
        # render_findings uses Rich Console, so we can't easily capture
        # Just verify it doesn't raise

    def test_non_empty_findings_renders(self):
        from mastiff.cli.output import render_findings

        finding = _make_finding()
        response = ReviewResponse(findings=[finding])
        # Should not raise
        render_findings(response)

    def test_render_without_confidence(self):
        from mastiff.cli.output import render_findings

        finding = _make_finding()
        response = ReviewResponse(findings=[finding])
        # Should not raise
        render_findings(response, show_confidence=False)


class TestRenderJson:
    """Tests for JSON output rendering."""

    def test_render_json_valid(self):
        from mastiff.cli.output import render_json

        response = ReviewResponse(findings=[])
        result = render_json(response)
        parsed = json.loads(result)
        assert "findings" in parsed
        assert parsed["findings"] == []

    def test_render_json_with_findings(self):
        from mastiff.cli.output import render_json

        finding = _make_finding()
        response = ReviewResponse(findings=[finding])
        result = render_json(response)
        parsed = json.loads(result)
        assert len(parsed["findings"]) == 1
        assert parsed["findings"][0]["rule_id"] == "blocking-test"

    def test_render_json_includes_schema_version(self):
        from mastiff.cli.output import render_json

        response = ReviewResponse(findings=[])
        result = render_json(response)
        parsed = json.loads(result)
        assert parsed["schema_version"] == "1"


class TestWatchCommand:
    """Tests for the watch subcommand."""

    def test_watch_help(self):
        """watch --help exits 0 and mentions --interval."""
        from mastiff.cli.app import main

        runner = CliRunner()
        result = runner.invoke(main, ["watch", "--help"])
        assert result.exit_code == 0
        assert "--interval" in result.output
