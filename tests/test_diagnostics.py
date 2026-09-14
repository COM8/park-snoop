"""Tests for redacted Park Snoop diagnostics."""

from types import SimpleNamespace

from custom_components.park_snoop.const import DOMAIN
from custom_components.park_snoop.diagnostics import (
    async_get_config_entry_diagnostics,
    redact_provider_detail,
)
from custom_components.park_snoop.models import Plate
from custom_components.park_snoop.runtime import ParkSnoopRuntime


class FakeScheduler:
    """Minimal scheduler double required by the diagnostics runtime fixture."""


async def test_diagnostics_redact_plate_and_provider_details() -> None:
    """Default diagnostics contain counts but never configured sensitive values."""
    runtime = ParkSnoopRuntime(
        FakeScheduler(),  # type: ignore[arg-type]
        (Plate("BAB123", display_name="Private car", notes="Sensitive"),),
    )

    hass = SimpleNamespace(data={DOMAIN: {"entry": runtime}})
    entry = SimpleNamespace(entry_id="entry")
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics == {"configured_plates": 1}  # noqa: S101
    assert "BAB123" not in str(diagnostics)  # noqa: S101
    assert "Private car" not in str(diagnostics)  # noqa: S101


def test_log_detail_redaction_never_returns_sensitive_input() -> None:
    """The log helper has no branch that can reveal provider response content."""
    detail = {"plate": "BAB123", "location": "Private"}
    assert redact_provider_detail(detail) == "<redacted>"  # noqa: S101
