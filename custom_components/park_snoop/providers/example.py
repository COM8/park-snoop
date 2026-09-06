"""Disabled template for authors adding a Park Snoop provider."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import NoRateLimitPolicy, Provider, ProviderError, ProviderMetadata

if TYPE_CHECKING:
    from custom_components.park_snoop.models import ProviderResult


class ExampleProvider(Provider):
    """Copy this class, implement it, then explicitly register the new provider."""

    metadata = ProviderMetadata(
        identifier="example", name="Example (disabled)", supports_batching=False
    )
    rate_limit_policy = NoRateLimitPolicy()

    async def async_query(self, plates: tuple[str, ...]) -> tuple[ProviderResult, ...]:
        """Refuse use until the template has an evidenced, safe implementation."""
        del plates
        raise ProviderError
