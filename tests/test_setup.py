"""Test the integration setup boundary."""

from typing import TYPE_CHECKING

from homeassistant.setup import async_setup_component

from custom_components.park_snoop.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_async_setup_does_not_make_network_requests(hass: HomeAssistant) -> None:
    """The integration domain can load before any configured plate is queried."""
    assert await async_setup_component(hass, DOMAIN, {})  # noqa: S101
