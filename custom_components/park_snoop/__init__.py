"""Park Snoop Home Assistant integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:  # noqa: ARG001
    """Set up the Park Snoop domain before config entries are created."""
    return True


async def async_setup_entry(_hass: HomeAssistant, _entry: ConfigEntry) -> bool:
    """
    Set up a Park Snoop config entry.

    Platform loading is intentionally added with the plate-monitoring runtime,
    so no blueprint coordinator or network client remains reachable here.
    """
    return True


async def async_unload_entry(_hass: HomeAssistant, _entry: ConfigEntry) -> bool:
    """Unload a Park Snoop config entry."""
    return True
