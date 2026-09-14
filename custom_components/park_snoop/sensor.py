"""Core Park Snoop parking-state entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, NAME

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .models import Plate
    from .runtime import ParkSnoopRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add status and active-session-count sensors for every configured plate."""
    runtime: ParkSnoopRuntime = hass.data[DOMAIN][entry.entry_id]
    entities = [
        entity
        for plate in runtime.plates
        for entity in (
            ParkingStatusSensor(runtime, plate),
            ActiveSessionsSensor(runtime, plate),
            LastCheckSensor(runtime, plate),
        )
    ]
    async_add_entities(entities)


class _PlateEntity(SensorEntity):
    """Common in-memory identity and device descriptor for a plate sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, runtime: ParkSnoopRuntime, plate: Plate, key: str) -> None:
        """Bind a sensor to a stable normalized plate identity."""
        self._runtime = runtime
        self._plate = plate
        plate_id = runtime.unique_id_for(plate)
        self._attr_unique_id = f"{plate_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, plate_id)}, name=plate.label, manufacturer=NAME
        )


class ParkingStatusSensor(_PlateEntity):
    """Expose the primary automation-friendly parking status."""

    _attr_name = None

    def __init__(self, runtime: ParkSnoopRuntime, plate: Plate) -> None:
        """Create the primary sensor for one plate device."""
        super().__init__(runtime, plate, "status")

    @property
    def native_value(self) -> str:
        """Return the cached aggregate status without provider I/O."""
        return self._runtime.aggregate_for(self._plate.identifier).status


class ActiveSessionsSensor(_PlateEntity):
    """Expose the active confirmed-or-possibly-active session count."""

    _attr_name = "Active sessions"

    def __init__(self, runtime: ParkSnoopRuntime, plate: Plate) -> None:
        """Create the count sensor for one plate device."""
        super().__init__(runtime, plate, "active_sessions")

    @property
    def native_value(self) -> int:
        """Return the cached active-session count without provider I/O."""
        return self._runtime.aggregate_for(self._plate.identifier).active_session_count


class LastCheckSensor(_PlateEntity):
    """Expose the newest completed provider check as a diagnostic timestamp."""

    _attr_name = "Last check"
    _attr_entity_category = "diagnostic"

    def __init__(self, runtime: ParkSnoopRuntime, plate: Plate) -> None:
        """Create the diagnostic timestamp sensor for one plate."""
        super().__init__(runtime, plate, "last_check")

    @property
    def native_value(self) -> datetime | None:
        """Return the cached last-check timestamp without provider I/O."""
        return self._runtime.last_check_for(self._plate.identifier)
