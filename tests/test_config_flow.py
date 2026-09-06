"""Tests for Park Snoop configuration and plate options flows."""

from typing import TYPE_CHECKING

from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.park_snoop.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_user_flow_creates_an_empty_registry(hass: HomeAssistant) -> None:
    """Initial setup does not require a network call or a first plate."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM  # noqa: S101
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY  # noqa: S101
    assert result["data"] == {}  # noqa: S101


async def test_options_add_plate_uses_defaults(hass: HomeAssistant) -> None:
    """A valid plate receives the five-minute and all-provider defaults."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"operation": "add"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"plate": "b ab-123", "display_name": "Car", "notes": "Private"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY  # noqa: S101
    assert result["data"]["plates"] == [  # noqa: S101
        {
            "identifier": "BAB123",
            "display_name": "Car",
            "notes": "Private",
            "frequency_minutes": 5,
            "provider_ids": ["betterpark", "parkdepot"],
        }
    ]


async def test_options_rejects_duplicate_plate_and_invalid_frequency(
    hass: HomeAssistant,
) -> None:
    """Invalid monitoring settings leave the existing plate registry untouched."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "plates": [
                {
                    "identifier": "BAB123",
                    "display_name": None,
                    "notes": None,
                    "frequency_minutes": 5,
                    "provider_ids": ["betterpark"],
                }
            ]
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"operation": "add"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"plate": "BAB-123", "frequency_minutes": 0}
    )

    assert result["type"] is FlowResultType.FORM  # noqa: S101
    assert result["errors"] == {  # noqa: S101
        "plate": "duplicate",
        "frequency_minutes": "invalid_frequency",
    }
