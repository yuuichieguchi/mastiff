"""Provider-related error classes for mastiff."""
from __future__ import annotations


class ProviderError(Exception):
    """Base error for provider-related failures."""


class MissingAPIKeyError(ProviderError):
    """API key environment variable not set."""


class MissingDependencyError(ProviderError):
    """Optional dependency not installed."""


class InvalidProviderError(ProviderError):
    """Unknown provider name in config."""


class CLINotFoundError(ProviderError):
    """CLI tool not found on PATH or not functional."""


class CLIOutputParseError(ProviderError):
    """Failed to parse CLI output into ReviewResponse."""
