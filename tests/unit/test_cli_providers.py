"""Tests for mastiff.analysis.cli_providers — CLI-based LLM providers.

Coverage:
- check_cli_available: PATH detection, version check, error handling
- _extract_claude_text: JSON, JSONL, plain text parsing
- _extract_codex_text: JSON, JSONL, plain text parsing
- ClaudeCodeProvider: protocol compliance, review(), error handling
- CodexProvider: protocol compliance, review(), error handling
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Valid ReviewResponse JSON used across provider tests
# ---------------------------------------------------------------------------

VALID_REVIEW_JSON = json.dumps(
    {
        "schema_version": "1",
        "findings": [
            {
                "schema_version": "1",
                "rule_id": "TEST-001",
                "category": "blocking",
                "severity": "warning",
                "file_path": "test.py",
                "line_start": 1,
                "title": "Test finding",
                "explanation": "Test explanation",
                "confidence": 0.9,
            }
        ],
    }
)


# ===========================================================================
# check_cli_available
# ===========================================================================


class TestCheckCliAvailable:
    """Tests for the check_cli_available utility function."""

    def test_should_return_true_when_cli_found_and_version_succeeds(self) -> None:
        """
        Given: shutil.which returns a path and run_command succeeds
        When: check_cli_available is called
        Then: returns True
        """
        from mastiff.analysis.cli_providers import check_cli_available

        with (
            patch("mastiff.analysis.cli_providers.shutil.which", return_value="/usr/bin/claude"),
            patch("mastiff.analysis.cli_providers.run_command") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="claude 1.0.0\n", returncode=0)
            result = check_cli_available("claude")

        assert result is True

    def test_should_return_false_when_cli_not_on_path(self) -> None:
        """
        Given: shutil.which returns None
        When: check_cli_available is called
        Then: returns False
        """
        from mastiff.analysis.cli_providers import check_cli_available

        with patch("mastiff.analysis.cli_providers.shutil.which", return_value=None):
            result = check_cli_available("claude")

        assert result is False

    def test_should_return_false_when_version_check_raises_subprocess_error(self) -> None:
        """
        Given: shutil.which returns a path but --version raises SubprocessError
        When: check_cli_available is called
        Then: returns False
        """
        from mastiff._internal.subprocess import SubprocessError
        from mastiff.analysis.cli_providers import check_cli_available

        with (
            patch("mastiff.analysis.cli_providers.shutil.which", return_value="/usr/bin/claude"),
            patch(
                "mastiff.analysis.cli_providers.run_command",
                side_effect=SubprocessError(
                    args=["claude", "--version"],
                    returncode=1,
                    stdout="",
                    stderr="command failed",
                ),
            ),
        ):
            result = check_cli_available("claude")

        assert result is False


# ===========================================================================
# _extract_claude_text
# ===========================================================================


class TestExtractClaudeText:
    """Tests for parsing claude CLI JSON output."""

    def test_should_extract_result_from_single_json_object(self) -> None:
        """
        Given: Single JSON line with type=result
        When: _extract_claude_text is called
        Then: returns the 'result' field value
        """
        from mastiff.analysis.cli_providers import _extract_claude_text

        stdout = json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "result": "review text here",
                "session_id": "abc",
            }
        )
        assert _extract_claude_text(stdout) == "review text here"

    def test_should_extract_result_from_jsonl_output(self) -> None:
        """
        Given: JSONL with assistant message then result line
        When: _extract_claude_text is called
        Then: returns the 'result' field from the result line
        """
        from mastiff.analysis.cli_providers import _extract_claude_text

        line1 = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "thinking..."}]
                },
            }
        )
        line2 = json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "result": "final answer",
                "session_id": "xyz",
            }
        )
        stdout = f"{line1}\n{line2}"
        assert _extract_claude_text(stdout) == "final answer"

    def test_should_return_text_as_is_when_not_json(self) -> None:
        """
        Given: Plain non-JSON text
        When: _extract_claude_text is called
        Then: returns the text as-is (fallback)
        """
        from mastiff.analysis.cli_providers import _extract_claude_text

        plain_text = "This is just plain text output"
        assert _extract_claude_text(plain_text) == plain_text


# ===========================================================================
# _extract_codex_text
# ===========================================================================


class TestExtractCodexText:
    """Tests for parsing codex CLI JSON output."""

    def test_should_extract_text_from_single_json_message(self) -> None:
        """
        Given: Single JSON with type=message and text content
        When: _extract_codex_text is called
        Then: returns the text from content
        """
        from mastiff.analysis.cli_providers import _extract_codex_text

        stdout = json.dumps(
            {
                "type": "message",
                "content": [{"type": "text", "text": "codex review"}],
            }
        )
        assert _extract_codex_text(stdout) == "codex review"

    def test_should_extract_text_from_last_jsonl_line(self) -> None:
        """
        Given: JSONL with multiple lines, last line has text content
        When: _extract_codex_text is called
        Then: returns text from the last line with text content
        """
        from mastiff.analysis.cli_providers import _extract_codex_text

        line1 = json.dumps(
            {
                "type": "message",
                "content": [{"type": "text", "text": "intermediate"}],
            }
        )
        line2 = json.dumps(
            {
                "type": "message",
                "content": [{"type": "text", "text": "final codex output"}],
            }
        )
        stdout = f"{line1}\n{line2}"
        assert _extract_codex_text(stdout) == "final codex output"

    def test_should_return_text_as_is_when_not_json(self) -> None:
        """
        Given: Plain non-JSON text
        When: _extract_codex_text is called
        Then: returns the text as-is (fallback)
        """
        from mastiff.analysis.cli_providers import _extract_codex_text

        plain_text = "Plain codex output"
        assert _extract_codex_text(plain_text) == plain_text


# ===========================================================================
# ClaudeCodeProvider
# ===========================================================================


class TestClaudeCodeProvider:
    """Tests for the ClaudeCodeProvider LLM provider."""

    def test_should_satisfy_llm_provider_protocol(self) -> None:
        """ClaudeCodeProvider must be a runtime-checkable LLMProvider."""
        from mastiff.analysis.cli_providers import ClaudeCodeProvider
        from mastiff.core.provider import LLMProvider

        provider = ClaudeCodeProvider(model="claude-opus-4-20250514", timeout=60)
        assert isinstance(provider, LLMProvider)

    @pytest.mark.asyncio
    async def test_review_should_return_review_response_with_findings(self) -> None:
        """
        Given: run_command returns valid claude JSON containing ReviewResponse
        When: review() is called
        Then: returns a ReviewResponse with the expected findings
        """
        from mastiff.analysis.cli_providers import ClaudeCodeProvider

        claude_output = json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "result": VALID_REVIEW_JSON,
                "session_id": "test-session",
            }
        )
        mock_result = MagicMock(stdout=claude_output, returncode=0)

        provider = ClaudeCodeProvider(model="claude-opus-4-20250514", timeout=60)

        with patch("mastiff.analysis.cli_providers.run_command", return_value=mock_result):
            response = await provider.review("Review this code")

        assert len(response.findings) == 1
        assert response.findings[0].rule_id == "TEST-001"
        assert response.findings[0].category.value == "blocking"

    @pytest.mark.asyncio
    async def test_review_should_pass_correct_cli_args(self) -> None:
        """
        Given: A ClaudeCodeProvider with a specific model
        When: review() is called
        Then: run_command is invoked with the correct arguments and input_text
        """
        from mastiff.analysis.cli_providers import ClaudeCodeProvider

        claude_output = json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "result": VALID_REVIEW_JSON,
                "session_id": "test-session",
            }
        )
        mock_result = MagicMock(stdout=claude_output, returncode=0)

        provider = ClaudeCodeProvider(model="my-model", timeout=120)

        mock_path = "mastiff.analysis.cli_providers.run_command"
        with patch(mock_path, return_value=mock_result) as mock_run:
            await provider.review("the prompt text")

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        expected_cmd = [
            "claude",
            "-p",
            "--output-format",
            "json",
            "--model",
            "my-model",
            "--tools",
            "",
        ]
        actual_cmd = call_args[0][0]
        assert (
            actual_cmd == expected_cmd
            or call_args.kwargs.get("args") == expected_cmd
            or list(actual_cmd) == expected_cmd
        )
        # Verify input_text is passed as the prompt
        input_kw = call_args.kwargs.get("input_text")
        input_pos = call_args[1].get("input_text") if len(call_args) > 1 else None
        assert input_kw == "the prompt text" or input_pos == "the prompt text"

    @pytest.mark.asyncio
    async def test_review_should_raise_provider_error_on_timeout(self) -> None:
        """
        Given: run_command raises SubprocessTimeoutError
        When: review() is called
        Then: raises ProviderError with 'timed out' in message
        """
        from mastiff._internal.subprocess import SubprocessTimeoutError
        from mastiff.analysis.cli_providers import ClaudeCodeProvider
        from mastiff.analysis.errors import ProviderError

        provider = ClaudeCodeProvider(model="m", timeout=60)

        with (
            patch(
                "mastiff.analysis.cli_providers.run_command",
                side_effect=SubprocessTimeoutError(args=["claude"], timeout=60.0),
            ),
            pytest.raises(ProviderError, match="(?i)timed out"),
        ):
            await provider.review("prompt")

    @pytest.mark.asyncio
    async def test_review_should_raise_provider_error_on_subprocess_error(self) -> None:
        """
        Given: run_command raises SubprocessError
        When: review() is called
        Then: raises ProviderError with stderr info
        """
        from mastiff._internal.subprocess import SubprocessError
        from mastiff.analysis.cli_providers import ClaudeCodeProvider
        from mastiff.analysis.errors import ProviderError

        provider = ClaudeCodeProvider(model="m", timeout=60)

        with (
            patch(
                "mastiff.analysis.cli_providers.run_command",
                side_effect=SubprocessError(
                    args=["claude"],
                    returncode=1,
                    stdout="",
                    stderr="some error details",
                ),
            ),
            pytest.raises(ProviderError),
        ):
            await provider.review("prompt")

    @pytest.mark.asyncio
    async def test_review_error_message_includes_command(self) -> None:
        """ProviderError from subprocess failure should include the failed command."""
        from mastiff._internal.subprocess import SubprocessError
        from mastiff.analysis.cli_providers import ClaudeCodeProvider
        from mastiff.analysis.errors import ProviderError

        provider = ClaudeCodeProvider(model="m", timeout=60)

        with (
            patch(
                "mastiff.analysis.cli_providers.run_command",
                side_effect=SubprocessError(
                    args=["claude"],
                    returncode=1,
                    stdout="",
                    stderr="unknown option",
                ),
            ),
            pytest.raises(ProviderError, match="cmd:"),
        ):
            await provider.review("prompt")

    @pytest.mark.asyncio
    async def test_review_should_raise_cli_output_parse_error_on_invalid_response(self) -> None:
        """
        Given: run_command returns output that cannot be parsed into ReviewResponse
        When: review() is called
        Then: raises CLIOutputParseError
        """
        from mastiff.analysis.cli_providers import ClaudeCodeProvider
        from mastiff.analysis.errors import CLIOutputParseError

        # Claude returns a result, but the result text is not valid ReviewResponse JSON
        claude_output = json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "result": "this is not valid review JSON",
                "session_id": "test-session",
            }
        )
        mock_result = MagicMock(stdout=claude_output, returncode=0)

        provider = ClaudeCodeProvider(model="m", timeout=60)

        with (
            patch("mastiff.analysis.cli_providers.run_command", return_value=mock_result),
            pytest.raises(CLIOutputParseError),
        ):
            await provider.review("prompt")


# ===========================================================================
# CodexProvider
# ===========================================================================


class TestCodexProvider:
    """Tests for the CodexProvider LLM provider."""

    def test_should_satisfy_llm_provider_protocol(self) -> None:
        """CodexProvider must be a runtime-checkable LLMProvider."""
        from mastiff.analysis.cli_providers import CodexProvider
        from mastiff.core.provider import LLMProvider

        provider = CodexProvider(model="codex-model", timeout=60)
        assert isinstance(provider, LLMProvider)

    @pytest.mark.asyncio
    async def test_review_should_return_review_response_with_findings(self) -> None:
        """
        Given: run_command returns valid codex JSON containing ReviewResponse
        When: review() is called
        Then: returns a ReviewResponse with the expected findings
        """
        from mastiff.analysis.cli_providers import CodexProvider

        codex_output = json.dumps(
            {
                "type": "message",
                "content": [{"type": "text", "text": VALID_REVIEW_JSON}],
            }
        )
        mock_result = MagicMock(stdout=codex_output, returncode=0)

        provider = CodexProvider(model="codex-model", timeout=60)

        with patch("mastiff.analysis.cli_providers.run_command", return_value=mock_result):
            response = await provider.review("Review this code")

        assert len(response.findings) == 1
        assert response.findings[0].rule_id == "TEST-001"

    @pytest.mark.asyncio
    async def test_review_should_pass_correct_cli_args(self) -> None:
        """
        Given: A CodexProvider with a specific model
        When: review() is called
        Then: run_command is invoked with the correct arguments and input_text
        """
        from mastiff.analysis.cli_providers import CodexProvider

        codex_output = json.dumps(
            {
                "type": "message",
                "content": [{"type": "text", "text": VALID_REVIEW_JSON}],
            }
        )
        mock_result = MagicMock(stdout=codex_output, returncode=0)

        provider = CodexProvider(model="my-codex-model", timeout=90)

        mock_path = "mastiff.analysis.cli_providers.run_command"
        with patch(mock_path, return_value=mock_result) as mock_run:
            await provider.review("the prompt text")

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        expected_cmd = [
            "codex", "exec", "--json",
            "--model", "my-codex-model", "-",
        ]
        actual_cmd = call_args[0][0]
        assert (
            actual_cmd == expected_cmd
            or call_args.kwargs.get("args") == expected_cmd
            or list(actual_cmd) == expected_cmd
        )
        # Verify input_text is passed as the prompt
        input_kw = call_args.kwargs.get("input_text")
        input_pos = call_args[1].get("input_text") if len(call_args) > 1 else None
        assert input_kw == "the prompt text" or input_pos == "the prompt text"

    @pytest.mark.asyncio
    async def test_review_should_raise_provider_error_on_timeout(self) -> None:
        """
        Given: run_command raises SubprocessTimeoutError
        When: review() is called
        Then: raises ProviderError
        """
        from mastiff._internal.subprocess import SubprocessTimeoutError
        from mastiff.analysis.cli_providers import CodexProvider
        from mastiff.analysis.errors import ProviderError

        provider = CodexProvider(model="m", timeout=60)

        with (
            patch(
                "mastiff.analysis.cli_providers.run_command",
                side_effect=SubprocessTimeoutError(args=["codex"], timeout=60.0),
            ),
            pytest.raises(ProviderError),
        ):
            await provider.review("prompt")

    @pytest.mark.asyncio
    async def test_review_should_raise_provider_error_on_subprocess_error(self) -> None:
        """
        Given: run_command raises SubprocessError
        When: review() is called
        Then: raises ProviderError
        """
        from mastiff._internal.subprocess import SubprocessError
        from mastiff.analysis.cli_providers import CodexProvider
        from mastiff.analysis.errors import ProviderError

        provider = CodexProvider(model="m", timeout=60)

        with (
            patch(
                "mastiff.analysis.cli_providers.run_command",
                side_effect=SubprocessError(
                    args=["codex"],
                    returncode=1,
                    stdout="",
                    stderr="codex error",
                ),
            ),
            pytest.raises(ProviderError),
        ):
            await provider.review("prompt")

    @pytest.mark.asyncio
    async def test_review_should_raise_cli_output_parse_error_on_invalid_response(self) -> None:
        """
        Given: run_command returns output that cannot be parsed into ReviewResponse
        When: review() is called
        Then: raises CLIOutputParseError
        """
        from mastiff.analysis.cli_providers import CodexProvider
        from mastiff.analysis.errors import CLIOutputParseError

        codex_output = json.dumps(
            {
                "type": "message",
                "content": [{"type": "text", "text": "not valid review json"}],
            }
        )
        mock_result = MagicMock(stdout=codex_output, returncode=0)

        provider = CodexProvider(model="m", timeout=60)

        with (
            patch("mastiff.analysis.cli_providers.run_command", return_value=mock_result),
            pytest.raises(CLIOutputParseError),
        ):
            await provider.review("prompt")


# ===========================================================================
# supports_runtime_model_override attribute
# ===========================================================================


class TestSupportsRuntimeModelOverride:
    """CLI providers should have supports_runtime_model_override = False."""

    def test_claude_code_provider_has_attribute(self) -> None:
        from mastiff.analysis.cli_providers import ClaudeCodeProvider

        provider = ClaudeCodeProvider(model="m", timeout=60)
        assert provider.supports_runtime_model_override is False

    def test_codex_provider_has_attribute(self) -> None:
        from mastiff.analysis.cli_providers import CodexProvider

        provider = CodexProvider(model="m", timeout=60)
        assert provider.supports_runtime_model_override is False
