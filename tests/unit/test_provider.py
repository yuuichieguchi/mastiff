"""Tests for sentinel.core.provider — LLMProvider Protocol."""
import pytest


class TestLLMProviderProtocol:
    """LLMProvider Protocol tests."""

    def test_protocol_is_runtime_checkable(self):
        from sentinel.core.provider import LLMProvider
        # Verify @runtime_checkable decorator is applied by checking isinstance works
        assert isinstance(type, type)  # sanity check
        # The real check is that isinstance() doesn't raise TypeError
        class Dummy:
            pass
        # If LLMProvider is not runtime_checkable, isinstance() raises TypeError
        result = isinstance(Dummy(), LLMProvider)
        assert result is False  # Dummy doesn't implement the protocol

    def test_fake_provider_satisfies_protocol(self):
        from sentinel.core.provider import LLMProvider
        from sentinel.core.models import ReviewResponse

        class FakeProvider:
            async def review(self, prompt: str, model: str | None = None) -> ReviewResponse:
                return ReviewResponse(findings=[])

        assert isinstance(FakeProvider(), LLMProvider)

    def test_invalid_provider_rejected(self):
        from sentinel.core.provider import LLMProvider

        class BadProvider:
            pass

        assert not isinstance(BadProvider(), LLMProvider)
