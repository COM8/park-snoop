"""Park Snoop Home Assistant integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .config_flow import PLATES
from .const import DOMAIN
from .models import Plate
from .providers.betterpark import BetterParkProvider
from .providers.parkdepot import ParkDepotProvider
from .providers.registry import ProviderRegistry
from .runtime import ParkSnoopRuntime
from .scheduler import MonitoringScheduler

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:  # noqa: ARG001
    """Set up the Park Snoop domain before config entries are created."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up a Park Snoop config entry.

    Set up providers, runtime state, and entity platforms for this entry.
    """
    plates = tuple(
        Plate(
            identifier=record["identifier"],
            display_name=record.get("display_name"),
            notes=record.get("notes"),
            frequency_minutes=record.get("frequency_minutes", 5),
            provider_ids=tuple(record.get("provider_ids", ())),
        )
        for record in entry.options.get(PLATES, [])
    )
    registry = ProviderRegistry()
    session = async_get_clientsession(hass)
    registry.register(BetterParkProvider(session))
    registry.register(ParkDepotProvider(session))
    scheduler = MonitoringScheduler(registry, lambda _results: None)
    runtime = ParkSnoopRuntime(scheduler, plates)
    scheduler.set_result_listener(runtime.async_handle_results)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime
    await runtime.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Park Snoop config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    runtime = hass.data[DOMAIN].pop(entry.entry_id)
    await runtime.async_stop()
    return unloaded
