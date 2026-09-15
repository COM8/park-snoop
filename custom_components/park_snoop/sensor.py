"""Core Park Snoop parking-state entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, NAME

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal

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
            NextCheckSensor(runtime, plate),
        )
    ]
    async_add_entities(entities)

    def add_currency_sensor(plate: Plate, currency: str) -> None:
        """Add one currency-specific monetary entity when it first appears."""
        async_add_entities([FeeTotalSensor(runtime, plate, currency)])

    runtime.add_currency_listener(add_currency_sensor)


class _PlateEntity(Entity):
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

    async def async_added_to_hass(self) -> None:
        """Subscribe this non-polling entity to normalized runtime updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._runtime.add_state_listener(
                self._plate.identifier, self.async_write_ha_state
            )
        )


class ParkingStatusSensor(_PlateEntity, SensorEntity):
    """Expose the primary automation-friendly parking status."""

    _attr_name = None

    def __init__(self, runtime: ParkSnoopRuntime, plate: Plate) -> None:
        """Create the primary sensor for one plate device."""
        super().__init__(runtime, plate, "status")

    @property
    def native_value(self) -> str:
        """Return the cached aggregate status without provider I/O."""
        return self._runtime.aggregate_for(self._plate.identifier).status

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Expose at most four normalized session details, never provider payloads."""
        aggregate = self._runtime.aggregate_for(self._plate.identifier)
        return {
            "fees_complete": aggregate.fees_complete,
            "sessions": [
                {
                    "provider": session.provider_id,
                    "confidence": session.confidence,
                    "started_at": session.started_at,
                    "fee_meaning": session.fee.meaning if session.fee else None,
                }
                for session in aggregate.sessions[:4]
            ],
        }


class ActiveSessionsSensor(_PlateEntity, SensorEntity):
    """Expose the active confirmed-or-possibly-active session count."""

    _attr_name = "Active sessions"

    def __init__(self, runtime: ParkSnoopRuntime, plate: Plate) -> None:
        """Create the count sensor for one plate device."""
        super().__init__(runtime, plate, "active_sessions")

    @property
    def native_value(self) -> int:
        """Return the cached active-session count without provider I/O."""
        return self._runtime.aggregate_for(self._plate.identifier).active_session_count


class LastCheckSensor(_PlateEntity, SensorEntity):
    """Expose the newest completed provider check as a diagnostic timestamp."""

    _attr_name = "Last check"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, runtime: ParkSnoopRuntime, plate: Plate) -> None:
        """Create the diagnostic timestamp sensor for one plate."""
        super().__init__(runtime, plate, "last_check")

    @property
    def native_value(self) -> datetime | None:
        """Return the cached last-check timestamp without provider I/O."""
        return self._runtime.last_check_for(self._plate.identifier)


class NextCheckSensor(_PlateEntity, SensorEntity):
    """Expose the next configured monitoring deadline as a diagnostic timestamp."""

    _attr_name = "Next check"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, runtime: ParkSnoopRuntime, plate: Plate) -> None:
        """Create the next-check diagnostic timestamp for one plate."""
        super().__init__(runtime, plate, "next_check")

    @property
    def native_value(self) -> datetime:
        """Return the cached cadence deadline without provider I/O."""
        return self._runtime.next_check_for(self._plate.identifier)


class FeeTotalSensor(_PlateEntity, SensorEntity):
    """Expose one currency-safe aggregate rather than an invalid cross-currency sum."""

    _attr_device_class = SensorDeviceClass.MONETARY

    def __init__(self, runtime: ParkSnoopRuntime, plate: Plate, currency: str) -> None:
        """Create a stable monetary sensor for one plate and ISO currency."""
        super().__init__(runtime, plate, f"fee_{currency.lower()}")
        self._currency = currency
        self._attr_name = f"Parking fees ({currency})"
        self._attr_native_unit_of_measurement = currency

    @property
    def native_value(self) -> Decimal | None:
        """Return only the cached total for this sensor's ISO currency."""
        return self._runtime.aggregate_for(self._plate.identifier).fee_totals.get(
            self._currency
        )
