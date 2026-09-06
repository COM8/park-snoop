"""Documented provider contract shared by all parking-service adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime, timedelta

    from custom_components.park_snoop.models import ProviderResult


class ProviderError(Exception):
    """Base error for a provider failure that can be shown without raw payloads."""


class ProviderRateLimitError(ProviderError):
    """Signal that a provider rejected a request and supplied an optional delay."""

    def __init__(self, retry_after_seconds: int | None = None) -> None:
        """Retain only the scheduler-safe retry time."""
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Provider rate limit reached")


class ProviderFormatError(ProviderError):
    """Signal an unexpected remote payload without retaining its contents."""


class ProviderTransientError(ProviderError):
    """Signal a retryable provider communication failure without raw details."""


@dataclass(frozen=True, slots=True)
class ProviderMetadata:
    """Immutable capabilities advertised by an independently replaceable adapter."""

    identifier: str
    name: str
    supports_batching: bool


class RateLimitPolicy(ABC):
    """Calculate provider-owned request eligibility for the central scheduler."""

    @abstractmethod
    def next_permitted_at(self, now: datetime) -> datetime:
        """Return the earliest time at which the next request may be sent."""

    @abstractmethod
    def record_request(self, at: datetime) -> None:
        """Observe a dispatched request so future eligibility remains accurate."""


class NoRateLimitPolicy(RateLimitPolicy):
    """Allow requests immediately when a provider has no known proactive limit."""

    def next_permitted_at(self, now: datetime) -> datetime:
        """Permit the request at the supplied instant."""
        return now

    def record_request(self, at: datetime) -> None:
        """Record nothing because this policy imposes no interval."""


class FixedIntervalRateLimitPolicy(RateLimitPolicy):
    """Permit one provider request per configured interval."""

    def __init__(self, interval: timedelta) -> None:
        """Create an interval policy with no prior request."""
        self._interval = interval
        self._last_request: datetime | None = None

    def next_permitted_at(self, now: datetime) -> datetime:
        """Return now or the end of the interval after the last request."""
        if self._last_request is None:
            return now
        return max(now, self._last_request + self._interval)

    def record_request(self, at: datetime) -> None:
        """Record the provider dispatch time."""
        self._last_request = at


class Provider(ABC):
    """Normalize provider APIs without exposing their wire format to Home Assistant."""

    metadata: ProviderMetadata
    rate_limit_policy: RateLimitPolicy

    @abstractmethod
    async def async_query(self, plates: tuple[str, ...]) -> tuple[ProviderResult, ...]:
        """Query one or more normalized plates and return only normalized results."""
