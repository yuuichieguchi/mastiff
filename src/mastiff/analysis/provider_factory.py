"""Provider factory for creating LLM providers based on config."""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from mastiff.analysis.errors import (
    CLINotFoundError,
    InvalidProviderError,
    MissingAPIKeyError,
)

if TYPE_CHECKING:
    from mastiff.config.schema import MastiffConfig
    from mastiff.core.provider import LLMProvider

logger = logging.getLogger(__name__)

_API_PROVIDER_DEFAULTS: dict[str, tuple[str, str]] = {
    # (env_var, default_model)
    "anthropic": ("ANTHROPIC_API_KEY", "claude-opus-4-20250514"),
    "openai": ("OPENAI_API_KEY", "gpt-4.1"),
}

_CLI_PROVIDER_DEFAULTS: dict[str, str] = {
    # cli_command_name — model is always None (let CLI decide)
    "claude-code": "claude",
    "codex": "codex",
}

_ALL_PROVIDERS = {*_API_PROVIDER_DEFAULTS, *_CLI_PROVIDER_DEFAULTS}


def default_api_key_env(provider: str) -> str:
    """Return the default API key environment variable for a provider."""
    return _API_PROVIDER_DEFAULTS[provider][0]


def default_model(provider: str) -> str:
    """Return the default model for an API provider."""
    return _API_PROVIDER_DEFAULTS[provider][1]


def create_provider(config: MastiffConfig) -> LLMProvider:
    """Create an LLM provider based on config and environment.

    Resolution order:
    1. Explicit config.api.provider -> use that provider
    2. provider is None -> auto-detect:
       a. claude CLI available -> claude-code
       b. codex CLI available -> codex
       c. ANTHROPIC_API_KEY -> anthropic
       d. OPENAI_API_KEY -> openai
       e. Neither -> MissingAPIKeyError
    """
    from mastiff.analysis.cli_providers import (
        ClaudeCodeProvider,
        CodexProvider,
        check_cli_available,
    )
    from mastiff.analysis.client import AnthropicProvider, OpenAIProvider

    provider_name = config.api.provider

    if provider_name is not None and provider_name not in _ALL_PROVIDERS:
        raise InvalidProviderError(
            f"Unknown provider: '{provider_name}'. "
            f"Supported: {', '.join(sorted(_ALL_PROVIDERS))}"
        )

    # --- Auto-detection ---
    if provider_name is None:
        # 1. CLI providers (preferred)
        if check_cli_available("claude"):
            logger.info("claude CLI detected, using claude-code provider")
            provider_name = "claude-code"
        elif check_cli_available("codex"):
            logger.info("codex CLI detected, using codex provider")
            provider_name = "codex"
        else:
            # 2. API key providers (fallback)
            has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
            has_openai = bool(os.environ.get("OPENAI_API_KEY"))

            if has_anthropic and has_openai:
                logger.info(
                    "Both API keys found, using Anthropic. Set api.provider to override."
                )
                provider_name = "anthropic"
            elif has_anthropic:
                provider_name = "anthropic"
            elif has_openai:
                provider_name = "openai"
            else:
                raise MissingAPIKeyError(
                    "Install claude or codex CLI, or set ANTHROPIC_API_KEY / OPENAI_API_KEY"
                )

    # --- CLI providers ---
    if provider_name in _CLI_PROVIDER_DEFAULTS:
        cli_cmd = _CLI_PROVIDER_DEFAULTS[provider_name]
        # Skip re-check when auto-detection already confirmed availability
        if config.api.provider is not None and not check_cli_available(cli_cmd):
            raise CLINotFoundError(f"CLI '{cli_cmd}' not found on PATH or not functional")

        # config.api.model is passed through as-is (None = let CLI decide)
        timeout = config.cost.max_api_seconds

        if provider_name == "claude-code":
            return ClaudeCodeProvider(model=config.api.model, timeout=timeout)
        return CodexProvider(model=config.api.model, timeout=timeout)

    # --- API providers ---
    env_var = config.api.api_key_env
    if env_var == "ANTHROPIC_API_KEY" and provider_name != "anthropic":
        env_var = default_api_key_env(provider_name)

    api_key = os.environ.get(env_var, "")
    if not api_key:
        raise MissingAPIKeyError(f"Set {env_var} environment variable")

    # None means user didn't specify -> use provider's default
    model = config.api.model or default_model(provider_name)

    if provider_name == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model)
    return OpenAIProvider(api_key=api_key, model=model)
