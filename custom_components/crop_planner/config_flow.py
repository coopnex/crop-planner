"""Adds config flow for Blueprint."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from slugify import slugify

from .const import CROP_PLANNER, DOMAIN, LOGGER


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


    # async def async_step_user_custom(
    #     self,
    #     user_input: dict | None = None,
    # ) -> config_entries.ConfigFlowResult:
    #     """Handle a flow initialized by the user."""
    #     _errors = {}
    #     if user_input is not None:
    #         await self.async_set_unique_id(unique_id=slugify(user_input["name"]))
    #         self._abort_if_unique_id_configured()
    #         return self.async_create_entry(
    #             title=user_input["name"],
    #             data=user_input,
    #         )

    #     return self.async_show_form(
    #         step_id="user",
    #         data_schema=vol.Schema(
    #             {
    #                 vol.Required(
    #                     "name",
    #                     default=(user_input or {}).get("name", vol.UNDEFINED),
    #                 ): selector.TextSelector(
    #                     selector.TextSelectorConfig(
    #                         type=selector.TextSelectorType.TEXT,
    #                     ),
    #                 ),
    #                 vol.Required(
    #                     "quantity",
    #                     default=(user_input or {}).get("quantity", 1),
    #                 ): selector.NumberSelector(
    #                     selector.NumberSelectorConfig(
    #                         mode=selector.NumberSelectorMode.BOX,
    #                         min=1,
    #                     ),
    #                 ),
    #             },
    #         ),
    #         errors=_errors,
    #     )

