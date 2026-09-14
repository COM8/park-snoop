"""Tests for stable, cached Park Snoop core entities."""

from custom_components.park_snoop.binary_sensor import ParkedIndicator
from custom_components.park_snoop.button import RecheckButton
from custom_components.park_snoop.models import Plate
from custom_components.park_snoop.runtime import ParkSnoopRuntime
from custom_components.park_snoop.sensor import (
    ActiveSessionsSensor,
    ParkingStatusSensor,
)
from tests.test_runtime import FakeScheduler


def test_core_entities_share_stable_plate_device_identity() -> None:
    """Status, count, and parked state are grouped under one opaque plate device."""
    plate = Plate("BAB123", display_name="Car")
    runtime = ParkSnoopRuntime(FakeScheduler(), (plate,))  # type: ignore[arg-type]
    status = ParkingStatusSensor(runtime, plate)
    count = ActiveSessionsSensor(runtime, plate)
    parked = ParkedIndicator(runtime, plate)

    assert status.native_value == "not_parked"  # noqa: S101
    assert count.native_value == 0  # noqa: S101
    assert parked.is_on is False  # noqa: S101
    assert status.device_info == count.device_info == parked.device_info  # noqa: S101
    assert status.unique_id != count.unique_id != parked.unique_id  # noqa: S101


async def test_recheck_button_requests_each_selected_provider() -> None:
    """The button delegates to scheduler-owned, deduplicated provider work."""
    plate = Plate("BAB123", provider_ids=("betterpark", "parkdepot"))
    scheduler = FakeScheduler()
    runtime = ParkSnoopRuntime(scheduler, (plate,))  # type: ignore[arg-type]

    await RecheckButton(runtime, plate).async_press()

    assert scheduler.requested == [  # noqa: S101
        ("BAB123", "betterpark"),
        ("BAB123", "parkdepot"),
    ]
