"""BetterPark's public plate-process adapter."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from custom_components.park_snoop.models import (
    Fee,
    FeeMeaning,
    ParkingSession,
    ProviderOutcome,
    ProviderResult,
    SessionConfidence,
)

from .base import (
    NoRateLimitPolicy,
    Provider,
    ProviderFormatError,
    ProviderMetadata,
    ProviderRateLimitError,
)

if TYPE_CHECKING:
    import aiohttp


class BetterParkProvider(Provider):
    """Read-only adapter for BetterPark's public plate-process endpoint."""

    metadata = ProviderMetadata(
        identifier="betterpark", name="BetterPark", supports_batching=False
    )

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Use Home Assistant's shared HTTP session for controlled requests."""
        self._session = session
        self.rate_limit_policy = NoRateLimitPolicy()

    @staticmethod
    def normalize_response(
        plate: str,
        status: int,
        payload: Any,
        checked_at: datetime,
        retry_after_seconds: int | None = None,
    ) -> ProviderResult:
        """Normalize a saved endpoint response without exposing raw JSON."""
        if status == HTTPStatus.TOO_MANY_REQUESTS:
            raise ProviderRateLimitError(retry_after_seconds)
        if status != HTTPStatus.OK or not isinstance(payload, list):
            raise ProviderFormatError
        if not payload:
            return ProviderResult(
                plate, "betterpark", checked_at, ProviderOutcome.NO_PARKING
            )
        sessions: list[ParkingSession] = []
        for process in payload:
            if not isinstance(process, dict) or not isinstance(process.get("id"), str):
                raise ProviderFormatError
            pending = bool(process.get("isPending")) or process.get("stop") is None
            if not pending:
                continue
            fee = None
            raw_fee = process.get("parkingFee")
            if isinstance(raw_fee, dict) and isinstance(raw_fee.get("currency"), str):
                try:
                    fee = Fee(
                        Decimal(str(raw_fee["value"])),
                        raw_fee["currency"],
                        FeeMeaning.ACCRUED_ESTIMATE,
                    )
                except KeyError, ArithmeticError:
                    raise ProviderFormatError from None
            area = process.get("area")
            location = area.get("displayName") if isinstance(area, dict) else None
            sessions.append(
                ParkingSession(
                    "betterpark",
                    process["id"],
                    SessionConfidence.CONFIRMED,
                    _parse_timestamp(process.get("start")),
                    location=location if isinstance(location, str) else None,
                    fee=fee,
                )
            )
        outcome = ProviderOutcome.SUCCESS if sessions else ProviderOutcome.NO_PARKING
        return ProviderResult(plate, "betterpark", checked_at, outcome, tuple(sessions))

    async def async_query(self, plates: tuple[str, ...]) -> tuple[ProviderResult, ...]:
        """Query BetterPark one plate at a time through its public GET endpoint."""
        results = []
        for plate in plates:
            url = f"https://pay.betterpark.de/api/parking-processes/{plate}"
            async with self._session.get(url) as response:
                retry_after = _retry_after_seconds(response.headers.get("Retry-After"))
                payload = await response.json(content_type=None)
                results.append(
                    self.normalize_response(
                        plate,
                        response.status,
                        payload,
                        datetime.now().astimezone(),
                        retry_after,
                    )
                )
        return tuple(results)


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse a provider ISO timestamp while treating absent timestamps as unknown."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _retry_after_seconds(value: str | None) -> int | None:
    """Parse a numeric Retry-After header; date forms are handled by the scheduler."""
    try:
        return max(0, int(value)) if value is not None else None
    except ValueError:
        return None
