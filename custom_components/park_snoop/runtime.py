"""Config-entry runtime state shared by the scheduler and entity platforms."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from .models import (
    AggregateState,
    Plate,
    ProviderResult,
    aggregate_sessions,
    plate_unique_id,
)

if TYPE_CHECKING:
    from .scheduler import MonitoringScheduler


class ParkSnoopRuntime:
    """Maintain the current plate registry while preserving stable plate identity."""

    def __init__(
        self, scheduler: MonitoringScheduler, plates: tuple[Plate, ...]
    ) -> None:
        """Create runtime state and schedule each configured plate-provider pair."""
        self.scheduler = scheduler
        self._plates = {plate.identifier: plate for plate in plates}
        self._results: dict[str, dict[str, ProviderResult]] = {}

    @property
    def plates(self) -> tuple[Plate, ...]:
        """Return the current records in deterministic identifier order."""
        return tuple(self._plates.values())

    def unique_id_for(self, plate: Plate) -> str:
        """Return the identity derived solely from the normalized plate identifier."""
        return plate_unique_id(plate.identifier)

    def aggregate_for(self, plate_id: str) -> AggregateState:
        """Return the current normalized aggregate for one configured plate."""
        sessions = [
            session
            for result in self._results.get(plate_id, {}).values()
            for session in result.sessions
        ]
        return aggregate_sessions(sessions)

    def last_check_for(self, plate_id: str) -> datetime | None:
        """Return the newest normalized provider check time for one plate."""
        checks = [
            result.checked_at for result in self._results.get(plate_id, {}).values()
        ]
        return max(checks, default=None)

    async def async_handle_results(self, results: tuple[ProviderResult, ...]) -> None:
        """Cache normalized results for entity properties without retaining payloads."""
        for result in results:
            if result.plate in self._plates:
                self._results.setdefault(result.plate, {})[result.provider_id] = result

    async def async_start(self) -> None:
        """Schedule current records before starting the entry-owned scheduler."""
        now = datetime.now(UTC)
        for plate in self._plates.values():
            for provider_id in plate.provider_ids:
                await self.scheduler.async_schedule(plate, provider_id, now)
        self.scheduler.async_start()

    async def async_reconfigure(self, plates: tuple[Plate, ...]) -> None:
        """Cancel removed records and schedule new records without changing IDs."""
        updated = {plate.identifier: plate for plate in plates}
        for plate_id in self._plates.keys() - updated.keys():
            await self.scheduler.async_cancel_plate(plate_id)
        self._plates = updated
        now = datetime.now(UTC)
        for plate in plates:
            for provider_id in plate.provider_ids:
                await self.scheduler.async_schedule(plate, provider_id, now)

    async def async_stop(self) -> None:
        """Stop all scheduler work when Home Assistant unloads the entry."""
        await self.scheduler.async_stop()

    async def async_request_recheck(self, plate_id: str) -> None:
        """Request immediate eligible work for every provider selected by a plate."""
        plate = self._plates[plate_id]
        for provider_id in plate.provider_ids:
            await self.scheduler.async_request_now(plate, provider_id)
