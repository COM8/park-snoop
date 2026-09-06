"""Tests for bounded scheduler error publication."""

from datetime import UTC, datetime

from custom_components.park_snoop.models import Plate, ProviderOutcome, ProviderResult
from custom_components.park_snoop.providers.base import (
    NoRateLimitPolicy,
    Provider,
    ProviderFormatError,
    ProviderMetadata,
)
from custom_components.park_snoop.providers.registry import ProviderRegistry
from custom_components.park_snoop.scheduler import MonitoringScheduler


class MalformedProvider(Provider):
    """A provider with a permanent response-format failure."""

    metadata = ProviderMetadata(
        identifier="malformed", name="Malformed", supports_batching=False
    )
    rate_limit_policy = NoRateLimitPolicy()

    async def async_query(self, plates: tuple[str, ...]) -> tuple[ProviderResult, ...]:
        """Fail without leaking any remote payload into the scheduler."""
        del plates
        raise ProviderFormatError


async def test_permanent_format_error_is_published_without_requeue() -> None:
    """Format errors become bounded error state and do not loop forever."""
    published: list[tuple[ProviderResult, ...]] = []
    registry = ProviderRegistry()
    registry.register(MalformedProvider())
    scheduler = MonitoringScheduler(registry, published.append)
    plate = Plate("BAB123", provider_ids=("malformed",))

    await scheduler.async_schedule(plate, "malformed", datetime.now(UTC))
    await scheduler.async_run_due()

    assert published[0][0].outcome is ProviderOutcome.ERROR  # noqa: S101
    assert scheduler.pending_keys == ()  # noqa: S101
