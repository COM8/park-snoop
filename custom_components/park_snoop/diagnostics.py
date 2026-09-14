"""Redacted diagnostics for Park Snoop's sensitive monitoring state."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runtime import ParkSnoopRuntime


async def async_get_config_entry_diagnostics(
    runtime: ParkSnoopRuntime,
) -> dict[str, int]:
    """Return bounded counts only; plates, locations, and responses stay private."""
    return {"configured_plates": len(runtime.plates)}
