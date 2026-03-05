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
