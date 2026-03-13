"""Adds config flow for Blueprint."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv, selector
from slugify import slugify

from .const import (
    ATTR_NAME,
    ATTR_QUANTITY,
    ATTR_SOWING_DATE,
    ATTR_SPECIES,
    CONF_CROPS,
    CROP_PLANNER,
    DOMAIN,
    LOGGER,
)
from .openplantbook import OpenPlantbookHelper

_CROP_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Optional(ATTR_QUANTITY, default=1): cv.positive_int,
        vol.Optional(ATTR_SOWING_DATE): selector.DateSelector(),
        vol.Optional(ATTR_SPECIES): cv.string,
    }
)


class CropPlannerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Crop Planner."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle user step."""
        if user_input is not None:
            await self.async_set_unique_id(unique_id=slugify(DOMAIN))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=CROP_PLANNER, data={CONF_CROPS: []})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return CropPlannerOptionsFlowHandler()


class CropPlannerOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for adding crop entities."""

    async def async_step_init(self, user_input=None):
        """Show menu: add a crop or finish."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_crop", "finish"],
        )

    async def async_step_add_crop(self, user_input=None):
        """Handle adding a new crop."""
        errors = {}
        if user_input is not None:
            image_url = None
            species = user_input.get(ATTR_SPECIES) or None
            if species:
                try:
                    opb_result = await OpenPlantbookHelper(self.hass).openplantbook_get(
                        species
                    )
                    if opb_result is not None:
                        image_url = opb_result.get("image_url")
                except Exception:  # noqa: BLE001
                    LOGGER.warning("OpenPlantbook lookup failed for species: %s", species)

            sowing_date = (
                user_input.get(ATTR_SOWING_DATE)
                or datetime.now(tz=UTC).date().isoformat()
            )
            new_crop = {
                "id": str(uuid.uuid4()),
                ATTR_NAME: user_input[ATTR_NAME],
                ATTR_QUANTITY: user_input.get(ATTR_QUANTITY, 1),
                ATTR_SOWING_DATE: sowing_date,
                ATTR_SPECIES: species,
                "image_url": image_url,
            }

            existing_crops = list(self.config_entry.data.get(CONF_CROPS, []))
            existing_crops.append(new_crop)
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, CONF_CROPS: existing_crops},
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="add_crop",
            data_schema=_CROP_SCHEMA,
            errors=errors,
        )

    async def async_step_finish(self, user_input=None):
        """Finish without adding a crop."""
        return self.async_create_entry(title="", data={})
