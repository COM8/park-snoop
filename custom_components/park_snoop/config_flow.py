"""Configuration and options flows for Park Snoop."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, NAME
from .models import normalize_plate

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.data_entry_flow import FlowResult

DEFAULT_FREQUENCY_MINUTES = 5
PLATES = "plates"
PROVIDERS = ("betterpark", "parkdepot")


class ParkSnoopConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create the single Park Snoop configuration entry."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Create an initially empty, local plate registry."""
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=NAME, data={})
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> ParkSnoopOptionsFlow:
        """Return the flow that maintains plate records in entry options."""
        return ParkSnoopOptionsFlow(config_entry)


class ParkSnoopOptionsFlow(config_entries.OptionsFlow):
    """Add, edit, and remove plate records without changing their identity."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Keep the config entry whose options this flow will replace."""
        self._config_entry = config_entry
        self._selected_plate: str | None = None

    @property
    def _plates(self) -> list[dict[str, Any]]:
        """Return a copy suitable for safe incremental flow updates."""
        return [dict(plate) for plate in self._config_entry.options.get(PLATES, [])]

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Choose the plate-registry operation."""
        if user_input is not None:
            operation = user_input["operation"]
            if operation == "add":
                return await self.async_step_add()
            if operation == "edit" and self._plates:
                return await self.async_step_select_edit()
            if operation == "remove" and self._plates:
                return await self.async_step_select_remove()
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Required("operation"): vol.In(("add", "edit", "remove"))}
            ),
        )

    async def async_step_add(self, user_input: dict | None = None) -> FlowResult:
        """Validate and append a new monitored plate."""
        errors: dict[str, str] = {}
        if user_input is not None:
            record, errors = self._validate_record(user_input)
            normalized = normalize_plate(str(user_input.get("plate", "")))
            if normalized in {plate["identifier"] for plate in self._plates}:
                errors["plate"] = "duplicate"
            if not errors and record:
                return self.async_create_entry(
                    title="", data={PLATES: [*self._plates, record]}
                )
        return self.async_show_form(
            step_id="add", data_schema=self._plate_schema(user_input), errors=errors
        )

    async def async_step_select_edit(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Select an existing plate to edit."""
        if user_input is not None:
            self._selected_plate = user_input["plate"]
            return await self.async_step_edit()
        return self.async_show_form(
            step_id="select_edit", data_schema=self._plate_choice_schema()
        )

    async def async_step_edit(self, user_input: dict | None = None) -> FlowResult:
        """Update metadata and monitoring choices for an existing plate."""
        selected = self._selected_plate
        if selected is None:
            return await self.async_step_select_edit()
        existing = next(
            plate for plate in self._plates if plate["identifier"] == selected
        )
        errors: dict[str, str] = {}
        if user_input is not None:
            record, errors = self._validate_record(user_input, identifier=selected)
            if not errors and record:
                return self.async_create_entry(
                    title="",
                    data={
                        PLATES: [
                            record if plate["identifier"] == selected else plate
                            for plate in self._plates
                        ]
                    },
                )
        return self.async_show_form(
            step_id="edit",
            data_schema=self._plate_schema(user_input or existing),
            errors=errors,
        )

    async def async_step_select_remove(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Remove a plate; runtime cancellation follows the options update."""
        if user_input is not None:
            selected = user_input["plate"]
            return self.async_create_entry(
                title="",
                data={
                    PLATES: [
                        plate
                        for plate in self._plates
                        if plate["identifier"] != selected
                    ]
                },
            )
        return self.async_show_form(
            step_id="select_remove", data_schema=self._plate_choice_schema()
        )

    def _plate_choice_schema(self) -> vol.Schema:
        """Build a deterministic selection schema from registered plates."""
        return vol.Schema(
            {
                vol.Required("plate"): vol.In(
                    {
                        plate["identifier"]: plate.get("display_name")
                        or plate["identifier"]
                        for plate in self._plates
                    }
                )
            }
        )

    def _plate_schema(self, values: dict[str, Any] | None = None) -> vol.Schema:
        """Render fields with safe defaults for a plate record."""
        values = values or {}
        return vol.Schema(
            {
                vol.Required("plate", default=values.get("identifier", "")): str,
                vol.Optional(
                    "display_name", default=values.get("display_name", "")
                ): str,
                vol.Optional("notes", default=values.get("notes", "")): str,
                vol.Optional(
                    "frequency_minutes",
                    default=values.get("frequency_minutes", DEFAULT_FREQUENCY_MINUTES),
                ): vol.Coerce(int),
                vol.Optional(
                    "provider_ids", default=values.get("provider_ids", list(PROVIDERS))
                ): [vol.In(PROVIDERS)],
            }
        )

    def _validate_record(
        self, user_input: dict[str, Any], identifier: str | None = None
    ) -> tuple[dict[str, Any] | None, dict[str, str]]:
        """Validate values independently so the UI can report every error."""
        errors: dict[str, str] = {}
        normalized = identifier or normalize_plate(str(user_input.get("plate", "")))
        frequency = user_input.get("frequency_minutes", DEFAULT_FREQUENCY_MINUTES)
        provider_ids = user_input.get("provider_ids", list(PROVIDERS))
        if not normalized:
            errors["plate"] = "invalid_plate"
        if not isinstance(frequency, int) or frequency < 1:
            errors["frequency_minutes"] = "invalid_frequency"
        if not provider_ids or any(
            provider not in PROVIDERS for provider in provider_ids
        ):
            errors["provider_ids"] = "invalid_providers"
        if errors:
            return None, errors
        return (
            {
                "identifier": normalized,
                "display_name": user_input.get("display_name") or None,
                "notes": user_input.get("notes") or None,
                "frequency_minutes": frequency,
                "provider_ids": list(provider_ids),
            },
            errors,
        )
