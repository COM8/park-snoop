"""Tests for deduplicated config-entry monitoring work."""

import asyncio
from datetime import UTC, datetime, timedelta

from custom_components.park_snoop.models import Plate, ProviderOutcome, ProviderResult
from custom_components.park_snoop.providers.base import (
    FixedIntervalRateLimitPolicy,
    NoRateLimitPolicy,
    Provider,
    ProviderMetadata,
    ProviderRateLimitError,
    ProviderTransientError,
)
from custom_components.park_snoop.providers.registry import ProviderRegistry
from custom_components.park_snoop.scheduler import MonitoringScheduler


class BlockingProvider(Provider):
    """A provider whose pending request lets the test attempt a duplicate."""

    metadata = ProviderMetadata(
        identifier="blocking", name="Blocking", supports_batching=False
    )
    rate_limit_policy = NoRateLimitPolicy()

    def __init__(self) -> None:
        """Initialize explicit synchronization points for the fake response."""
        self.calls: list[tuple[str, ...]] = []
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def async_query(self, plates: tuple[str, ...]) -> tuple[ProviderResult, ...]:
        """Wait for the test before returning one no-parking result per plate."""
        self.calls.append(plates)
        self.started.set()
        await self.release.wait()
        now = datetime.now(UTC)
        return tuple(
            ProviderResult(plate, "blocking", now, ProviderOutcome.NO_PARKING)
            for plate in plates
        )


class RecordingProvider(Provider):
    """A provider that records dispatch shape for scheduler coalescing tests."""

    def __init__(self, identifier: str, *, supports_batching: bool) -> None:
        """Create a fake provider with one declared query capability."""
        self.metadata = ProviderMetadata(identifier, identifier, supports_batching)
        self.rate_limit_policy = NoRateLimitPolicy()
        self.calls: list[tuple[str, ...]] = []

    async def async_query(self, plates: tuple[str, ...]) -> tuple[ProviderResult, ...]:
        """Record the request and return a no-parking result for each plate."""
        self.calls.append(plates)
        now = datetime.now(UTC)
        return tuple(
            ProviderResult(
                plate, self.metadata.identifier, now, ProviderOutcome.NO_PARKING
            )
            for plate in plates
        )


async def test_manual_request_does_not_duplicate_a_running_plate_provider_job() -> None:
    """A manual refresh shares the in-flight provider work for the same key."""
    provider = BlockingProvider()
    registry = ProviderRegistry()
    registry.register(provider)
    scheduler = MonitoringScheduler(registry, lambda _results: None)
    plate = Plate("BAB123", provider_ids=("blocking",))

    await scheduler.async_schedule(plate, "blocking", datetime.now(UTC))
    running = asyncio.create_task(scheduler.async_run_due())
    await provider.started.wait()
    await scheduler.async_request_now(plate, "blocking")
    provider.release.set()
    await running

    assert provider.calls == [("BAB123",)]  # noqa: S101


async def test_stop_cancels_the_config_entry_scheduler_task() -> None:
    """Stopping an entry scheduler cancels its sleeper and clears future work."""
    provider = BlockingProvider()
    registry = ProviderRegistry()
    registry.register(provider)
    scheduler = MonitoringScheduler(registry, lambda _results: None)
    plate = Plate("BAB123", provider_ids=("blocking",))

    await scheduler.async_schedule(
        plate, "blocking", datetime.now(UTC) + timedelta(hours=1)
    )
    scheduler.async_start()
    await scheduler.async_stop()

    assert scheduler.is_running is False  # noqa: S101
    assert scheduler.pending_keys == ()  # noqa: S101


async def test_scheduler_batches_only_batch_capable_provider_jobs() -> None:
    """Same-time due plates are grouped only when their provider supports it."""
    batched = RecordingProvider("batched", supports_batching=True)
    individual = RecordingProvider("individual", supports_batching=False)
    registry = ProviderRegistry()
    registry.register(batched)
    registry.register(individual)
    scheduler = MonitoringScheduler(registry, lambda _results: None)
    first = Plate("BAB123", provider_ids=("batched", "individual"))
    second = Plate("MUC456", provider_ids=("batched", "individual"))
    now = datetime.now(UTC)

    for plate in (first, second):
        for provider_id in plate.provider_ids:
            await scheduler.async_schedule(plate, provider_id, now)
    await scheduler.async_run_due()

    assert batched.calls == [("BAB123", "MUC456")]  # noqa: S101
    assert individual.calls == [("BAB123",), ("MUC456",)]  # noqa: S101


async def test_scheduler_defers_proactively_rate_limited_work() -> None:
    """A provider policy delays work without making an HTTP request."""
    provider = RecordingProvider("limited", supports_batching=False)
    provider.rate_limit_policy = FixedIntervalRateLimitPolicy(timedelta(minutes=5))
    registry = ProviderRegistry()
    registry.register(provider)
    now = datetime.now(UTC)
    provider.rate_limit_policy.record_request(now)
    scheduler = MonitoringScheduler(registry, lambda _results: None, now=lambda: now)
    plate = Plate("BAB123", provider_ids=("limited",))

    await scheduler.async_schedule(plate, "limited", now)
    await scheduler.async_run_due()

    assert provider.calls == []  # noqa: S101
    assert scheduler.pending_keys == (("BAB123", "limited"),)  # noqa: S101


class RateLimitedProvider(RecordingProvider):
    """A fake provider that tells the scheduler to retry later."""

    async def async_query(self, plates: tuple[str, ...]) -> tuple[ProviderResult, ...]:
        """Simulate an HTTP 429 with no usable Retry-After value."""
        self.calls.append(plates)
        raise ProviderRateLimitError


async def test_rate_limit_without_retry_after_requeues_for_one_minute() -> None:
    """Missing Retry-After gets the required minimum one-minute deferment."""
    now = datetime.now(UTC)
    provider = RateLimitedProvider("limited", supports_batching=False)
    registry = ProviderRegistry()
    registry.register(provider)
    scheduler = MonitoringScheduler(registry, lambda _results: None, now=lambda: now)
    plate = Plate("BAB123", provider_ids=("limited",))

    await scheduler.async_schedule(plate, "limited", now)
    await scheduler.async_run_due()

    assert provider.calls == [("BAB123",)]  # noqa: S101
    assert scheduler.pending_keys == (("BAB123", "limited"),)  # noqa: S101


class TransientProvider(RecordingProvider):
    """A fake provider that fails temporarily without exposing an HTTP payload."""

    async def async_query(self, plates: tuple[str, ...]) -> tuple[ProviderResult, ...]:
        """Simulate a retryable connection failure."""
        self.calls.append(plates)
        raise ProviderTransientError


async def test_transient_failure_uses_bounded_deterministic_backoff() -> None:
    """The injected jitter makes retry timing deterministic under test."""
    now = datetime.now(UTC)
    provider = TransientProvider("transient", supports_batching=False)
    registry = ProviderRegistry()
    registry.register(provider)
    scheduler = MonitoringScheduler(
        registry,
        lambda _results: None,
        now=lambda: now,
        jitter_seconds=lambda: 2,
    )
    plate = Plate("BAB123", provider_ids=("transient",))

    await scheduler.async_schedule(plate, "transient", now)
    await scheduler.async_run_due()

    assert scheduler.next_due_at == now + timedelta(seconds=17)  # noqa: S101
