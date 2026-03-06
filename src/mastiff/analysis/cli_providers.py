"""CLI-based LLM providers that shell out to ``claude`` and ``codex`` CLIs."""

from __future__ import annotations

import json
import logging
import shlex
import shutil
from typing import TYPE_CHECKING

from mastiff._internal.subprocess import SubprocessError, SubprocessTimeoutError, run_command
from mastiff.analysis.errors import CLIOutputParseError, ProviderError
from mastiff.analysis.response import parse_response

if TYPE_CHECKING:
    from mastiff.core.models import ReviewResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def check_cli_available(cli_name: str) -> bool:
    """Check whether a CLI tool is installed and functional.

    Uses ``shutil.which`` to locate the binary, then runs
    ``<cli_name> --version`` to verify it is executable.

    Args:
        cli_name: Name of the CLI binary (e.g. ``"claude"`` or ``"codex"``).

    Returns:
        ``True`` if the CLI is found on PATH and responds to ``--version``.
    """
    if shutil.which(cli_name) is None:
        return False
    try:
        run_command([cli_name, "--version"], timeout=10)
    except SubprocessError:
        return False
    return True


# ---------------------------------------------------------------------------
# Output extractors
# ---------------------------------------------------------------------------


def _extract_claude_text(stdout: str) -> str:
    """Extract the review text from ``claude --output-format json`` output.

    The Claude CLI emits either a single JSON object or multiple JSONL lines.
    We look for the object with ``"type": "result"`` and return its
    ``"result"`` field.

    Falls back to returning *stdout* as-is when no structured result is found.
    """
    # Try single JSON object
    try:
        data = json.loads(stdout)
        if isinstance(data, dict) and data.get("type") == "result" and "result" in data:
            return str(data["result"])
    except (json.JSONDecodeError, ValueError):
        pass

    # Try JSONL (one JSON object per line)
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if isinstance(data, dict) and data.get("type") == "result" and "result" in data:
                return str(data["result"])
        except (json.JSONDecodeError, ValueError):
            continue

    # Fallback — let parse_response() deal with the raw text
    return stdout


def _extract_codex_error(stdout: str) -> str:
    """Extract error messages from codex JSONL output.

    When codex exits with non-zero and empty stderr, the error info
    lives in stdout as JSONL events with ``"type": "error"`` or
    ``"type": "turn.failed"``.
    """
    messages: list[str] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        if data.get("type") == "error" and "message" in data:
            messages.append(data["message"])
        elif data.get("type") == "turn.failed":
            err = data.get("error", {})
            if isinstance(err, dict) and "message" in err:
                messages.append(err["message"])
    return "; ".join(messages) if messages else "(no error details in stdout)"


def _extract_codex_text(stdout: str) -> str:
    """Extract the review text from ``codex exec --json`` output.

    The Codex CLI emits JSONL events.  We handle two known formats:

    1. ``{"content": [{"type": "text", "text": "..."}]}`` — older/wrapper format
    2. ``{"type": "item.completed", "item": {"text": "..."}}`` — streaming JSONL

    We return the *last* text found across all lines.  Falls back to returning
    *stdout* as-is when no structured result is found.
    """
    last_text: str | None = None

    def _try_extract(obj: object) -> str | None:
        if not isinstance(obj, dict):
            return None
        # Format 1: content list
        content = obj.get("content")
        if isinstance(content, list):
            found: str | None = None
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text" and "text" in item:
                    found = item["text"]
            if found is not None:
                return found
        # Format 2: item.completed events
        if obj.get("type") == "item.completed":
            item = obj.get("item")
            if isinstance(item, dict) and "text" in item:
                return str(item["text"])
        return None

    # Try single JSON object
    try:
        data = json.loads(stdout)
        text = _try_extract(data)
        if text is not None:
            last_text = text
    except (json.JSONDecodeError, ValueError):
        pass

    if last_text is not None:
        return last_text

    # Try JSONL
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            text = _try_extract(data)
            if text is not None:
                last_text = text
        except (json.JSONDecodeError, ValueError):
            continue

    if last_text is not None:
        return last_text

    # Fallback
    return stdout


# ---------------------------------------------------------------------------
# Provider classes
# ---------------------------------------------------------------------------


class ClaudeCodeProvider:
    """LLM provider that uses the ``claude`` CLI for code review."""

    supports_runtime_model_override: bool = False

    def __init__(self, model: str, timeout: int) -> None:
        self._model = model
        self._timeout = timeout

    async def review(self, prompt: str, model: str | None = None) -> ReviewResponse:
        """Run a code review via the Claude CLI.

        Args:
            prompt: The fully-built review prompt.
            model: Optional model override (uses configured model if ``None``).

        Returns:
            Parsed ``ReviewResponse``.

        Raises:
            ProviderError: On CLI timeout or subprocess failure.
            CLIOutputParseError: When CLI output cannot be parsed.
        """
        use_model = model or self._model
        cmd = [
            "claude",
            "-p",
            "--output-format",
            "json",
            "--model",
            use_model,
            "--tools",
            "",
        ]
        try:
            result = run_command(cmd, timeout=self._timeout, input_text=prompt, check=True)
        except SubprocessTimeoutError:
            raise ProviderError(f"CLI timed out after {self._timeout}s") from None
        except SubprocessError as exc:
            cmd_str = shlex.join(cmd)
            raise ProviderError(
                f"claude CLI failed (cmd: {cmd_str}): {exc.stderr.strip()}"
            ) from None

        text = _extract_claude_text(result.stdout)
        response = parse_response(text)
        if response is None:
            logger.debug("Claude CLI stdout (first 500 chars): %s", result.stdout[:500])
            logger.debug("Extracted text (first 500 chars): %s", text[:500])
            raise CLIOutputParseError(
                "Failed to parse claude CLI output into ReviewResponse. "
                f"Extracted text (first 200 chars): {text[:200]}"
            )
        return response


class CodexProvider:
    """LLM provider that uses the ``codex`` CLI for code review."""

    supports_runtime_model_override: bool = False

    def __init__(self, model: str, timeout: int) -> None:
        self._model = model
        self._timeout = timeout

    async def review(self, prompt: str, model: str | None = None) -> ReviewResponse:
        """Run a code review via the Codex CLI.

        Args:
            prompt: The fully-built review prompt.
            model: Optional model override (uses configured model if ``None``).

        Returns:
            Parsed ``ReviewResponse``.

        Raises:
            ProviderError: On CLI timeout or subprocess failure.
            CLIOutputParseError: When CLI output cannot be parsed.
        """
        use_model = model or self._model
        cmd = ["codex", "exec", "--json", "--model", use_model, "-"]
        try:
            result = run_command(cmd, timeout=self._timeout, input_text=prompt, check=True)
        except SubprocessTimeoutError:
            raise ProviderError(f"CLI timed out after {self._timeout}s") from None
        except SubprocessError as exc:
            cmd_str = shlex.join(cmd)
            detail = exc.stderr.strip()
            if not detail:
                detail = _extract_codex_error(exc.stdout)
            raise ProviderError(
                f"codex CLI failed (cmd: {cmd_str}): {detail}"
            ) from None

        text = _extract_codex_text(result.stdout)
        response = parse_response(text)
        if response is None:
            logger.debug("Codex CLI stdout (first 500 chars): %s", result.stdout[:500])
            logger.debug("Extracted text (first 500 chars): %s", text[:500])
            raise CLIOutputParseError(
                "Failed to parse codex CLI output into ReviewResponse. "
                f"Extracted text (first 200 chars): {text[:200]}"
            )
        return response
