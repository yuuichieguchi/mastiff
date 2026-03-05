"""Tests for AI agent integrations — Claude Code, Codex, agent output format."""
from __future__ import annotations

import json
import os
import stat
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from pathlib import Path
import pytest

from mastiff.core.models import (
    DetectionCategory,
    FindingSchema,
    ReviewResponse,
)
from mastiff.core.severity import Severity


def _make_finding(**kwargs) -> FindingSchema:
    defaults = {
        "rule_id": "blocking-sync-in-async",
        "category": DetectionCategory.BLOCKING,
        "severity": Severity.CRITICAL,
        "file_path": "src/api/users.py",
        "line_start": 42,
        "title": "time.sleep() blocks the event loop in async handler",
        "explanation": "Blocking call in async context",
        "confidence": 0.9,
    }
    defaults.update(kwargs)
    return FindingSchema(**defaults)


class TestRenderAgent:
    """Tests for render_agent(response) from mastiff.cli.output."""

    def test_empty_findings_returns_empty(self) -> None:
        """render_agent(ReviewResponse(findings=[])) returns empty string."""
        from mastiff.cli.output import render_agent

        response = ReviewResponse(findings=[])
        result = render_agent(response)
        assert result == ""

    def test_single_finding_format(self) -> None:
        """Single finding output contains [CRITICAL], file path, line number, rule_id, title."""
        from mastiff.cli.output import render_agent

        finding = _make_finding()
        response = ReviewResponse(findings=[finding])
        result = render_agent(response)

        assert "[CRITICAL]" in result
        assert "src/api/users.py" in result
        assert "42" in result
        assert "blocking-sync-in-async" in result
        assert "time.sleep() blocks the event loop in async handler" in result

    def test_finding_with_suggested_fix(self) -> None:
        """Finding with suggested_fix includes FIX: prefix in output."""
        from mastiff.cli.output import render_agent

        finding = _make_finding(suggested_fix="Use await asyncio.sleep(n)")
        response = ReviewResponse(findings=[finding])
        result = render_agent(response)

        assert "FIX: Use await asyncio.sleep(n)" in result

    def test_finding_without_suggested_fix(self) -> None:
        """Finding without suggested_fix does not contain FIX: in output."""
        from mastiff.cli.output import render_agent

        finding = _make_finding()
        assert finding.suggested_fix is None
        response = ReviewResponse(findings=[finding])
        result = render_agent(response)

        assert "FIX:" not in result

    def test_no_ansi_codes(self) -> None:
        """Agent output has no ANSI escape sequences."""
        from mastiff.cli.output import render_agent

        finding = _make_finding()
        response = ReviewResponse(findings=[finding])
        result = render_agent(response)

        assert "\x1b[" not in result

    def test_multiple_findings(self) -> None:
        """Two findings result in output containing both rule_ids."""
        from mastiff.cli.output import render_agent

        finding1 = _make_finding(rule_id="blocking-sync-in-async")
        finding2 = _make_finding(
            rule_id="resource-leak-unclosed-file",
            category=DetectionCategory.RESOURCE_LEAK,
            severity=Severity.WARNING,
            title="Unclosed file handle",
        )
        response = ReviewResponse(findings=[finding1, finding2])
        result = render_agent(response)

        assert "blocking-sync-in-async" in result
        assert "resource-leak-unclosed-file" in result


class TestClaudeCodeHooks:
    """Tests for install_hooks(project_dir) from mastiff.integrations.claude_code."""

    def test_creates_hook_script(self, tmp_path: Path) -> None:
        """Creates .claude/hooks/mastiff-review.sh that is executable
        and contains mastiff review."""
        from mastiff.integrations.claude_code import install_hooks

        install_hooks(tmp_path)

        hook_path = tmp_path / ".claude" / "hooks" / "mastiff-review.sh"
        assert hook_path.exists()
        assert os.access(hook_path, os.X_OK)
        file_stat = hook_path.stat()
        assert file_stat.st_mode & stat.S_IXUSR  # 0o755 check
        assert "mastiff review" in hook_path.read_text()

    def test_creates_settings_local_json(self, tmp_path: Path) -> None:
        """Creates .claude/settings.local.json with hooks.PostToolUse containing Mastiff entry."""
        from mastiff.integrations.claude_code import install_hooks

        install_hooks(tmp_path)

        settings_path = tmp_path / ".claude" / "settings.local.json"
        assert settings_path.exists()
        data = json.loads(settings_path.read_text())
        assert "hooks" in data
        assert "PostToolUse" in data["hooks"]
        hook_entries = data["hooks"]["PostToolUse"]
        assert isinstance(hook_entries, list)
        # At least one entry should reference Mastiff and match Edit|Write
        mastiff_entries = [
            e for e in hook_entries if "mastiff" in json.dumps(e).lower()
        ]
        assert len(mastiff_entries) >= 1
        mastiff_entry = mastiff_entries[0]
        assert "Edit" in str(mastiff_entry.get("matcher", "")) or "Write" in str(
            mastiff_entry.get("matcher", "")
        )

    def test_idempotent(self, tmp_path: Path) -> None:
        """Running install_hooks twice produces same result, no duplicate entries."""
        from mastiff.integrations.claude_code import install_hooks

        install_hooks(tmp_path)
        install_hooks(tmp_path)

        settings_path = tmp_path / ".claude" / "settings.local.json"
        data = json.loads(settings_path.read_text())
        hook_entries = data["hooks"]["PostToolUse"]
        mastiff_entries = [
            e for e in hook_entries if "mastiff" in json.dumps(e).lower()
        ]
        assert len(mastiff_entries) == 1

    def test_merges_existing_settings(self, tmp_path: Path) -> None:
        """If settings.local.json already has other hooks,
        Mastiff entry is added without removing existing ones."""
        from mastiff.integrations.claude_code import install_hooks

        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir(parents=True, exist_ok=True)
        existing_settings = {
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": ["echo 'hello'"],
                    }
                ]
            }
        }
        (settings_dir / "settings.local.json").write_text(json.dumps(existing_settings))

        install_hooks(tmp_path)

        data = json.loads((settings_dir / "settings.local.json").read_text())
        hook_entries = data["hooks"]["PostToolUse"]
        # Original entry still present
        bash_entries = [e for e in hook_entries if e.get("matcher") == "Bash"]
        assert len(bash_entries) == 1
        # Mastiff entry also present
        mastiff_entries = [
            e for e in hook_entries if "mastiff" in json.dumps(e).lower()
        ]
        assert len(mastiff_entries) >= 1

    def test_malformed_json_raises(self, tmp_path: Path) -> None:
        """If settings.local.json contains invalid JSON,
        raises click.ClickException with 'Corrupt'."""
        from mastiff.integrations.claude_code import install_hooks

        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir(parents=True, exist_ok=True)
        (settings_dir / "settings.local.json").write_text("{invalid json!!!")

        with pytest.raises(click.ClickException, match="Corrupt"):
            install_hooks(tmp_path)


class TestCodexHooks:
    """Tests for install_hooks(project_dir) from mastiff.integrations.codex."""

    def test_creates_post_commit_hook(self, tmp_path: Path) -> None:
        """Creates .git/hooks/post-commit, is executable, contains mastiff review."""
        from mastiff.integrations.codex import install_hooks

        git_hooks = tmp_path / ".git" / "hooks"
        git_hooks.mkdir(parents=True, exist_ok=True)

        install_hooks(tmp_path)

        hook_path = git_hooks / "post-commit"
        assert hook_path.exists()
        assert os.access(hook_path, os.X_OK)
        assert "mastiff review" in hook_path.read_text()

    def test_chains_existing_hook(self, tmp_path: Path) -> None:
        """If .git/hooks/post-commit exists, backs it up and chains it."""
        from mastiff.integrations.codex import install_hooks

        git_hooks = tmp_path / ".git" / "hooks"
        git_hooks.mkdir(parents=True, exist_ok=True)
        existing_hook = git_hooks / "post-commit"
        existing_hook.write_text("#!/bin/sh\necho 'existing hook'\n")
        existing_hook.chmod(0o755)

        install_hooks(tmp_path)

        backup_path = git_hooks / "post-commit.pre-mastiff"
        assert backup_path.exists()
        assert "existing hook" in backup_path.read_text()

        new_hook = git_hooks / "post-commit"
        new_hook_text = new_hook.read_text()
        assert "post-commit.pre-mastiff" in new_hook_text
        assert "mastiff review" in new_hook_text

    def test_idempotent_with_marker(self, tmp_path: Path) -> None:
        """Running twice doesn't duplicate entries. Uses # --- mastiff-hook-start --- marker."""
        from mastiff.integrations.codex import install_hooks

        git_hooks = tmp_path / ".git" / "hooks"
        git_hooks.mkdir(parents=True, exist_ok=True)

        install_hooks(tmp_path)
        install_hooks(tmp_path)

        hook_path = git_hooks / "post-commit"
        hook_text = hook_path.read_text()
        assert hook_text.count("# --- mastiff-hook-start ---") == 1
        assert hook_text.count("mastiff review") == 1
