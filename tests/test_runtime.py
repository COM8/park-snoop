"""Tests for stable plate identity and runtime reconfiguration."""

from typing import TYPE_CHECKING

from custom_components.park_snoop.models import Plate
from custom_components.park_snoop.runtime import ParkSnoopRuntime

if TYPE_CHECKING:
    from datetime import datetime


class FakeScheduler:
    """Minimal scheduler double that exposes configuration-side effects."""

    def __init__(self) -> None:
        """Create empty records for scheduling and cancellation calls."""
        self.scheduled: list[tuple[str, str]] = []
        self.cancelled: list[str] = []

    async def async_schedule(
        self, plate: Plate, provider_id: str, due_at: datetime
    ) -> None:
        """Record a scheduled pair without executing provider work."""
        del due_at
        self.scheduled.append((plate.identifier, provider_id))

    async def async_cancel_plate(self, plate_id: str) -> None:
        """Record cancellation for a removed plate."""
        self.cancelled.append(plate_id)

    def async_start(self) -> None:
        """Provide the runtime's expected scheduler startup hook."""

    async def async_stop(self) -> None:
        """Provide the runtime's expected scheduler shutdown hook."""


async def test_rename_preserves_stable_plate_identity() -> None:
    """Changing UI metadata never changes the runtime's plate-derived ID."""
    scheduler = FakeScheduler()
    original = Plate("BAB123", display_name="Car", provider_ids=("betterpark",))
    runtime = ParkSnoopRuntime(scheduler, (original,))  # type: ignore[arg-type]
    original_id = runtime.unique_id_for(original)

    renamed = Plate("BAB123", display_name="Family car", provider_ids=("betterpark",))
    await runtime.async_reconfigure((renamed,))

    assert runtime.unique_id_for(renamed) == original_id  # noqa: S101
    assert scheduler.cancelled == []  # noqa: S101


async def test_removal_cancels_queued_plate_work() -> None:
    """Removing a record asks the scheduler to discard only that plate's jobs."""
    scheduler = FakeScheduler()
    plate = Plate("BAB123", provider_ids=("betterpark", "parkdepot"))
    runtime = ParkSnoopRuntime(scheduler, (plate,))  # type: ignore[arg-type]

    await runtime.async_reconfigure(())

    assert scheduler.cancelled == ["BAB123"]  # noqa: S101
