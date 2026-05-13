"""Adds config flow for Blueprint."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from .const import (
    ATTR_NAME,
    ATTR_QUANTITY,
    ATTR_SPECIES,
    CONF_CROPS,
    CROP_PHASES,
    CROP_PLANNER,
    DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.data_entry_flow import FlowResult

_NO_SPECIES = "__none__"

_CROP_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Optional(ATTR_QUANTITY, default=1): cv.positive_int,
        vol.Optional(ATTR_SPECIES): cv.string,
    }
)


def _phases_schema() -> vol.Schema:
    """Build a schema with optional start/end DateSelector for each phase."""
    fields: dict[vol.Optional, Any] = {}
    for phase in CROP_PHASES:
        fields[vol.Optional(f"{phase}")] = selector.DateSelector()
    return vol.Schema(fields)


class CropPlannerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Crop Planner."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user step."""
        if user_input is not None:
            await self.async_set_unique_id(unique_id=DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=CROP_PLANNER,
                data={CONF_CROPS: []},
            )
        return self.async_show_form(step_id="user", errors={})

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,  # noqa: ARG004
    ) -> CropPlannerOptionsFlowHandler:
        """Return the options flow handler."""
        return CropPlannerOptionsFlowHandler()


class CropPlannerOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for adding crop entities."""

    def __init__(self) -> None:
        """Initialize the options flow."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,  # noqa: ARG002
    ) -> FlowResult:
        """Show menu: add a crop, remove a crop, or finish."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["remove_crops", "clear_todos"],
        )

    async def async_step_remove_crops(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user pick one or more crops to delete."""
        existing_crops: list[dict] = list(self.config_entry.data.get(CONF_CROPS, []))

        if user_input is not None:
            if user_input.get("remove_all"):
                updated_crops = []
            else:
                ids_to_remove = set(user_input.get("crop_ids", []))
                updated_crops = [
                    c for c in existing_crops if c["id"] not in ids_to_remove
                ]
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, CONF_CROPS: updated_crops},
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        options = [
            selector.SelectOptionDict(value=c["id"], label=c.get(ATTR_NAME, c["id"]))
            for c in existing_crops
        ]
        return self.async_show_form(
            step_id="remove_crops",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "remove_all", default=False
                    ): selector.BooleanSelector(),
                    vol.Optional("crop_ids", default=[]): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=options, multiple=True)
                    ),
                }
            ),
        )

    async def async_step_clear_todos(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Clear all todo items after confirmation."""
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, "todos": []},
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(step_id="clear_todos")
