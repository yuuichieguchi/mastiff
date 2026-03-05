"""Tests for mastiff.analysis.provider_factory — provider auto-detection and creation."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class TestProviderErrors:
    """Verify custom error classes and their inheritance."""

    def test_provider_error_hierarchy(self):
        from mastiff.analysis.errors import (
            InvalidProviderError,
            MissingAPIKeyError,
            MissingDependencyError,
            ProviderError,
        )

        assert issubclass(MissingAPIKeyError, ProviderError)
        assert issubclass(MissingDependencyError, ProviderError)
        assert issubclass(InvalidProviderError, ProviderError)

    def test_missing_api_key_error_is_exception(self):
        from mastiff.analysis.errors import MissingAPIKeyError

        assert issubclass(MissingAPIKeyError, Exception)

    def test_missing_dependency_error_is_exception(self):
        from mastiff.analysis.errors import MissingDependencyError

        assert issubclass(MissingDependencyError, Exception)

    def test_invalid_provider_error_is_exception(self):
        from mastiff.analysis.errors import InvalidProviderError

        assert issubclass(InvalidProviderError, Exception)


# ---------------------------------------------------------------------------
# create_provider factory
# ---------------------------------------------------------------------------


class TestCreateProvider:
    """Tests for the create_provider(config) factory function."""

    # ==================== Helpers ====================

    @staticmethod
    def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
        """Remove both provider API keys from the environment."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # ==================== Explicit provider selection ====================

    def test_explicit_anthropic(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When config.api.provider = 'anthropic' and ANTHROPIC_API_KEY is set,
        create_provider returns an AnthropicProvider."""
        from mastiff.analysis.client import AnthropicProvider
        from mastiff.analysis.provider_factory import create_provider
        from mastiff.config.schema import ApiConfig, MastiffConfig

        self._clear_env(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        config = MastiffConfig(api=ApiConfig(provider="anthropic"))
        provider = create_provider(config)

        assert isinstance(provider, AnthropicProvider)

    def test_explicit_openai(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When config.api.provider = 'openai' and OPENAI_API_KEY is set,
        create_provider returns an OpenAIProvider."""
        self._clear_env(monkeypatch)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test-key")

        # Mock the openai package so it's importable
        mock_openai = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_openai}):
            from mastiff.analysis.provider_factory import create_provider
            from mastiff.config.schema import ApiConfig, MastiffConfig

            config = MastiffConfig(api=ApiConfig(provider="openai"))
            provider = create_provider(config)

            # Should be an OpenAIProvider (from mastiff.analysis.client)
            assert type(provider).__name__ == "OpenAIProvider"

    # ==================== Auto-detection ====================

    def test_auto_detect_anthropic_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When provider=None and only ANTHROPIC_API_KEY is set,
        auto-detect returns AnthropicProvider."""
        from mastiff.analysis.client import AnthropicProvider
        from mastiff.analysis.provider_factory import create_provider
        from mastiff.config.schema import ApiConfig, MastiffConfig

        self._clear_env(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-auto")

        with patch(
            "mastiff.analysis.cli_providers.check_cli_available",
            return_value=False,
        ):
            config = MastiffConfig(api=ApiConfig(provider=None))
            provider = create_provider(config)

        assert isinstance(provider, AnthropicProvider)

    def test_auto_detect_openai_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When provider=None and only OPENAI_API_KEY is set,
        auto-detect returns OpenAIProvider."""
        self._clear_env(monkeypatch)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-auto")

        mock_openai = MagicMock()
        with (
            patch.dict("sys.modules", {"openai": mock_openai}),
            patch(
                "mastiff.analysis.cli_providers.check_cli_available",
                return_value=False,
            ),
        ):
            from mastiff.analysis.provider_factory import create_provider
            from mastiff.config.schema import ApiConfig, MastiffConfig

            config = MastiffConfig(api=ApiConfig(provider=None))
            provider = create_provider(config)

            assert type(provider).__name__ == "OpenAIProvider"

    def test_auto_detect_both_prefers_anthropic(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """When provider=None and both API keys are set,
        auto-detect returns AnthropicProvider and logs an info message."""
        from mastiff.analysis.client import AnthropicProvider
        from mastiff.analysis.provider_factory import create_provider
        from mastiff.config.schema import ApiConfig, MastiffConfig

        self._clear_env(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-both")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-both")

        config = MastiffConfig(api=ApiConfig(provider=None))

        with (
            patch(
                "mastiff.analysis.cli_providers.check_cli_available",
                return_value=False,
            ),
            caplog.at_level(logging.INFO),
        ):
            provider = create_provider(config)

        assert isinstance(provider, AnthropicProvider)
        # Should log an info message about the auto-detection preference
        assert any("anthropic" in record.message.lower() for record in caplog.records)

    # ==================== Error cases ====================

    def test_auto_detect_neither_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When provider=None and no API keys are set, raises MissingAPIKeyError."""
        from mastiff.analysis.errors import MissingAPIKeyError
        from mastiff.analysis.provider_factory import create_provider
        from mastiff.config.schema import ApiConfig, MastiffConfig

        self._clear_env(monkeypatch)

        config = MastiffConfig(api=ApiConfig(provider=None))

        with (
            patch(
                "mastiff.analysis.cli_providers.check_cli_available",
                return_value=False,
            ),
            pytest.raises(MissingAPIKeyError),
        ):
            create_provider(config)

    def test_invalid_provider_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When provider='gemini' (unsupported), raises InvalidProviderError."""
        from mastiff.analysis.errors import InvalidProviderError
        from mastiff.analysis.provider_factory import create_provider
        from mastiff.config.schema import ApiConfig, MastiffConfig

        self._clear_env(monkeypatch)

        config = MastiffConfig(api=ApiConfig(provider="gemini"))

        with pytest.raises(InvalidProviderError):
            create_provider(config)

    def test_openai_missing_dependency(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When provider='openai', OPENAI_API_KEY is set, but the openai
        package is not installed, raises MissingDependencyError."""
        from mastiff.analysis.errors import MissingDependencyError
        from mastiff.analysis.provider_factory import create_provider
        from mastiff.config.schema import ApiConfig, MastiffConfig

        self._clear_env(monkeypatch)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-nodep")

        # Make openai import fail
        with patch.dict("sys.modules", {"openai": None}):
            config = MastiffConfig(api=ApiConfig(provider="openai"))

            with pytest.raises(MissingDependencyError):
                create_provider(config)


# ---------------------------------------------------------------------------
# CLI providers via create_provider
# ---------------------------------------------------------------------------


class TestCLIProviders:
    """Tests for CLI provider creation through the provider factory."""

    @staticmethod
    def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
        """Remove all provider-related env vars."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def test_explicit_claude_code_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When provider='claude-code' and CLI is available,
        create_provider returns a ClaudeCodeProvider."""
        from mastiff.analysis.cli_providers import ClaudeCodeProvider
        from mastiff.analysis.provider_factory import create_provider
        from mastiff.config.schema import ApiConfig, MastiffConfig

        self._clear_env(monkeypatch)

        with patch(
            "mastiff.analysis.cli_providers.check_cli_available",
            return_value=True,
        ):
            config = MastiffConfig(api=ApiConfig(provider="claude-code"))
            provider = create_provider(config)

        assert isinstance(provider, ClaudeCodeProvider)

    def test_explicit_codex_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When provider='codex' and CLI is available,
        create_provider returns a CodexProvider."""
        from mastiff.analysis.cli_providers import CodexProvider
        from mastiff.analysis.provider_factory import create_provider
        from mastiff.config.schema import ApiConfig, MastiffConfig

        self._clear_env(monkeypatch)

        with patch(
            "mastiff.analysis.cli_providers.check_cli_available",
            return_value=True,
        ):
            config = MastiffConfig(api=ApiConfig(provider="codex"))
            provider = create_provider(config)

        assert isinstance(provider, CodexProvider)

    def test_explicit_claude_code_not_available_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When provider='claude-code' but CLI is not available,
        create_provider raises CLINotFoundError."""
        from mastiff.analysis.errors import CLINotFoundError
        from mastiff.analysis.provider_factory import create_provider
        from mastiff.config.schema import ApiConfig, MastiffConfig

        self._clear_env(monkeypatch)

        with (
            patch(
                "mastiff.analysis.cli_providers.check_cli_available",
                return_value=False,
            ),
            pytest.raises(CLINotFoundError),
        ):
            config = MastiffConfig(api=ApiConfig(provider="claude-code"))
            create_provider(config)

    def test_auto_detect_claude_cli_when_no_api_keys(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When provider=None, no API keys, but claude CLI is available,
        auto-detect returns ClaudeCodeProvider."""
        from mastiff.analysis.cli_providers import ClaudeCodeProvider
        from mastiff.analysis.provider_factory import create_provider
        from mastiff.config.schema import ApiConfig, MastiffConfig

        self._clear_env(monkeypatch)

        def cli_available(name: str) -> bool:
            return name == "claude"

        with patch(
            "mastiff.analysis.cli_providers.check_cli_available",
            side_effect=cli_available,
        ):
            config = MastiffConfig(api=ApiConfig(provider=None))
            provider = create_provider(config)

        assert isinstance(provider, ClaudeCodeProvider)

    def test_auto_detect_falls_through_to_api_when_no_cli(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When provider=None, no CLIs available, but ANTHROPIC_API_KEY set,
        falls through to API and returns AnthropicProvider."""
        from mastiff.analysis.client import AnthropicProvider
        from mastiff.analysis.provider_factory import create_provider
        from mastiff.config.schema import ApiConfig, MastiffConfig

        self._clear_env(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        with patch(
            "mastiff.analysis.cli_providers.check_cli_available",
            return_value=False,
        ):
            config = MastiffConfig(api=ApiConfig(provider=None))
            provider = create_provider(config)

        assert isinstance(provider, AnthropicProvider)

    def test_auto_detect_prefers_cli_over_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When provider=None, claude CLI is available AND ANTHROPIC_API_KEY is set,
        CLI is preferred — returns ClaudeCodeProvider."""
        from mastiff.analysis.cli_providers import ClaudeCodeProvider
        from mastiff.analysis.provider_factory import create_provider
        from mastiff.config.schema import ApiConfig, MastiffConfig

        self._clear_env(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        def cli_available(name: str) -> bool:
            return name == "claude"

        with patch(
            "mastiff.analysis.cli_providers.check_cli_available",
            side_effect=cli_available,
        ):
            config = MastiffConfig(api=ApiConfig(provider=None))
            provider = create_provider(config)

        assert isinstance(provider, ClaudeCodeProvider)

    def test_auto_detect_nothing_available_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When provider=None, no CLIs, no API keys — raises MissingAPIKeyError."""
        from mastiff.analysis.errors import MissingAPIKeyError
        from mastiff.analysis.provider_factory import create_provider
        from mastiff.config.schema import ApiConfig, MastiffConfig

        self._clear_env(monkeypatch)

        with (
            patch(
                "mastiff.analysis.cli_providers.check_cli_available",
                return_value=False,
            ),
            pytest.raises(MissingAPIKeyError),
        ):
            config = MastiffConfig(api=ApiConfig(provider=None))
            create_provider(config)
