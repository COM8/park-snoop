"""Park Snoop parked-indicator entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntity

from .sensor import _PlateEntity

if TYPE_CHECKING:
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
    """Add one parked indicator for every configured plate."""
    runtime: ParkSnoopRuntime = hass.data["park_snoop"][entry.entry_id]
    async_add_entities(ParkedIndicator(runtime, plate) for plate in runtime.plates)


class ParkedIndicator(_PlateEntity, BinarySensorEntity):
    """Indicate whether cached results show one or more active sessions."""

    _attr_icon = "mdi:car"
    _attr_translation_key = "parked"

    def __init__(self, runtime: ParkSnoopRuntime, plate: Plate) -> None:
        """Create a parked indicator for one stable plate device."""
        super().__init__(runtime, plate, "parked")

    @property
    def is_on(self) -> bool:
        """Return whether cached aggregate state has any active session."""
        aggregate = self._runtime.aggregate_for(self._plate.identifier)
        return aggregate.active_session_count > 0
