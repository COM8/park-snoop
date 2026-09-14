"""Redacted diagnostics for Park Snoop's sensitive monitoring state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .runtime import ParkSnoopRuntime


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, int]:
    """Return bounded counts only; plates, locations, and responses stay private."""
    runtime: ParkSnoopRuntime = hass.data[DOMAIN][entry.entry_id]
    return {"configured_plates": len(runtime.plates)}


def redact_provider_detail(value: object) -> str:
    """Return a fixed safe marker instead of plate, location, or payload content."""
    del value
    return "<redacted>"
