"""Offline Home Assistant setup coverage for Park Snoop plate entities."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest  # noqa: TC002
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.park_snoop.const import DOMAIN
from custom_components.park_snoop.models import (
    Fee,
    FeeMeaning,
    ParkingSession,
    ProviderOutcome,
    ProviderResult,
    SessionConfidence,
)
from custom_components.park_snoop.scheduler import MonitoringScheduler

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_entry_setup_adds_stable_plate_entities(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The actual config-entry path creates core entities under one plate device."""
    monkeypatch.setattr(MonitoringScheduler, "async_start", lambda _self: None)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "plates": [
                {
                    "identifier": "BAB123",
                    "display_name": "Car",
                    "frequency_minutes": 5,
                    "provider_ids": ["betterpark"],
                }
            ]
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)  # noqa: S101
    await hass.async_block_till_done()

    assert hass.states.get("sensor.car") is not None  # noqa: S101
    assert hass.states.get("sensor.car_active_sessions") is not None  # noqa: S101
    assert hass.states.get("binary_sensor.car_parked") is not None  # noqa: S101

    runtime = hass.data[DOMAIN][entry.entry_id]
    await runtime.async_handle_results(
        (
            ProviderResult(
                "BAB123",
                "betterpark",
                datetime(2026, 9, 15, tzinfo=UTC),
                ProviderOutcome.SUCCESS,
                (
                    ParkingSession(
                        "betterpark",
                        "session",
                        SessionConfidence.CONFIRMED,
                        fee=Fee(2, "EUR", FeeMeaning.ACCRUED_ESTIMATE),
                    ),
                ),
            ),
        )
    )
    await hass.async_block_till_done()

    assert hass.states.get("sensor.car").state == "parking"  # noqa: S101
    assert hass.states.get("sensor.car_active_sessions").state == "1"  # noqa: S101
    assert hass.states.get("binary_sensor.car_parked").state == "on"  # noqa: S101
    fee = hass.states.get("sensor.car_parking_fees_eur")
    assert fee.state == "2"  # noqa: S101
    assert fee.attributes["unit_of_measurement"] == "EUR"  # noqa: S101

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.car_recheck"},
        blocking=True,
    )
    assert runtime.scheduler.pending_keys == (("BAB123", "betterpark"),)  # noqa: S101

    hass.config_entries.async_update_entry(
        entry,
        options={
            "plates": [
                {
                    "identifier": "BAB123",
                    "display_name": "Family car",
                    "frequency_minutes": 5,
                    "provider_ids": ["betterpark"],
                }
            ]
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.car") is not None  # noqa: S101

    hass.config_entries.async_update_entry(entry, options={"plates": []})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.car") is None  # noqa: S101

    assert await hass.config_entries.async_unload(entry.entry_id)  # noqa: S101
