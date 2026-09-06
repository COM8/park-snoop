"""Tests for the provider extension contract and registry."""

from datetime import UTC, datetime

from custom_components.park_snoop.models import ProviderOutcome, ProviderResult
from custom_components.park_snoop.providers.base import (
    NoRateLimitPolicy,
    Provider,
    ProviderMetadata,
)
from custom_components.park_snoop.providers.registry import ProviderRegistry


class FakeProvider(Provider):
    """A minimal batch-capable provider used to prove contract conformance."""

    metadata = ProviderMetadata(identifier="fake", name="Fake", supports_batching=True)
    rate_limit_policy = NoRateLimitPolicy()

    async def async_query(self, plates: tuple[str, ...]) -> tuple[ProviderResult, ...]:
        """Return a successful empty result for each requested plate."""
        now = datetime.now(UTC)
        return tuple(
            ProviderResult(
                plate, self.metadata.identifier, now, ProviderOutcome.NO_PARKING
            )
            for plate in plates
        )


async def test_provider_registry_accepts_contract_conforming_provider() -> None:
    """Registered providers expose their immutable metadata and normalized result."""
    registry = ProviderRegistry()
    provider = FakeProvider()
    registry.register(provider)

    assert registry.get("fake") is provider  # noqa: S101
    result = await provider.async_query(("BAB123",))
    assert result[0].outcome is ProviderOutcome.NO_PARKING  # noqa: S101
