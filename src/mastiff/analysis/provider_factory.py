"""Provider factory for creating LLM providers based on config."""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from mastiff.analysis.errors import (
    InvalidProviderError,
    MissingAPIKeyError,
)

if TYPE_CHECKING:
    from mastiff.config.schema import MastiffConfig
    from mastiff.core.provider import LLMProvider

logger = logging.getLogger(__name__)

_PROVIDER_DEFAULTS: dict[str, tuple[str, str]] = {
    "anthropic": ("ANTHROPIC_API_KEY", "claude-opus-4-20250514"),
    "openai": ("OPENAI_API_KEY", "gpt-4.1"),
}


def default_api_key_env(provider: str) -> str:
    """Return the default API key environment variable for a provider."""
    return _PROVIDER_DEFAULTS[provider][0]


def default_model(provider: str) -> str:
    """Return the default model for a provider."""
    return _PROVIDER_DEFAULTS[provider][1]


def create_provider(config: MastiffConfig) -> LLMProvider:
    """Create an LLM provider based on config and environment.

    Resolution order:
    1. Explicit config.api.provider -> use that provider
    2. provider is None -> auto-detect from environment variables
       - ANTHROPIC_API_KEY only -> anthropic
       - OPENAI_API_KEY only -> openai
       - Both -> anthropic (with log info)
       - Neither -> MissingAPIKeyError
    """
    from mastiff.analysis.client import AnthropicProvider, OpenAIProvider

    provider_name = config.api.provider

    if provider_name is not None and provider_name not in _PROVIDER_DEFAULTS:
        raise InvalidProviderError(
            f"Unknown provider: '{provider_name}'. Supported: anthropic, openai"
        )

    if provider_name is None:
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
                "Set ANTHROPIC_API_KEY or OPENAI_API_KEY, or set api.provider in config"
            )

    env_var = config.api.api_key_env
    if env_var == "ANTHROPIC_API_KEY" and provider_name != "anthropic":
        env_var = default_api_key_env(provider_name)

    api_key = os.environ.get(env_var, "")
    if not api_key:
        raise MissingAPIKeyError(f"Set {env_var} environment variable")

    model = config.api.model
    if model == default_model("anthropic") and provider_name != "anthropic":
        model = default_model(provider_name)

    if provider_name == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model)
    return OpenAIProvider(api_key=api_key, model=model)
