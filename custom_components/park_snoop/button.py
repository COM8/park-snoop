"""Park Snoop manual refresh buttons."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity

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
    """Add one scheduler-backed recheck button for every configured plate."""
    runtime: ParkSnoopRuntime = hass.data["park_snoop"][entry.entry_id]
    async_add_entities(RecheckButton(runtime, plate) for plate in runtime.plates)


class RecheckButton(_PlateEntity, ButtonEntity):
    """Ask the scheduler for an immediate eligible check without bypassing limits."""

    _attr_name = "Recheck"

    def __init__(self, runtime: ParkSnoopRuntime, plate: Plate) -> None:
        """Create a recheck control for one stable plate device."""
        super().__init__(runtime, plate, "recheck")

    async def async_press(self) -> None:
        """Delegate rechecking to the scheduler's deduplicated request path."""
        await self._runtime.async_request_recheck(self._plate.identifier)
