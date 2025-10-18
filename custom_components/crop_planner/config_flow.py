"""Adds config flow for Blueprint."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from slugify import slugify

from .const import CROP_PLANNER, DOMAIN


class CropPlannerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle user step."""
        _errors = {}
        if user_input is not None:
            await self.async_set_unique_id(unique_id=slugify(CROP_PLANNER))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=CROP_PLANNER,
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            errors=_errors,
        )
