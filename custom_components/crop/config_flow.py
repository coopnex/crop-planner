"""Adds config flow for Blueprint."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from slugify import slugify

from .const import (
    ATTR_NAME,
    ATTR_QUANTITY,
    ATTR_SPECIES,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_CROPS,
    CROP_PHASES,
    CROP_PLANNER,
    DOMAIN,
    LOGGER,
    OPB_DISPLAY_PID,
    OPB_PID,
    PHASE_SOWING,
)
from .openplantbook import OpenPlantbookHelper

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
            await self.async_set_unique_id(unique_id=slugify(DOMAIN))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=CROP_PLANNER,
                data={
                    CONF_CROPS: [],
                    CONF_CLIENT_ID: user_input.get(CONF_CLIENT_ID, ""),
                    CONF_CLIENT_SECRET: user_input.get(CONF_CLIENT_SECRET, ""),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_CLIENT_ID, default=""): cv.string,
                    vol.Optional(CONF_CLIENT_SECRET, default=""): cv.string,
                }
            ),
        )

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
        self._crop_base: dict[str, Any] = {}
        self._pending_species: str | None = None
        self._pending_image_url: str | None = None
        self._species_options: list[selector.SelectOptionDict] = []
        self._last_search_hint: str = ""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,  # noqa: ARG002
    ) -> FlowResult:
        """Show menu: add a crop, remove a crop, or finish."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_crop", "remove_crops", "clear_todos", "finish"],
        )

    async def async_step_remove_crops(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user pick one or more crops to delete."""
        existing_crops: list[dict] = list(self.config_entry.data.get(CONF_CROPS, []))

        if user_input is not None:
            ids_to_remove = set(user_input.get("crop_ids", []))
            updated_crops = [c for c in existing_crops if c["id"] not in ids_to_remove]
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
                    vol.Required("crop_ids"): selector.SelectSelector(
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

    async def async_step_add_crop(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the crop form; proceed to species selection if a hint is given."""
        if user_input is not None:
            self._crop_base = {
                ATTR_NAME: user_input[ATTR_NAME],
                ATTR_QUANTITY: user_input.get(ATTR_QUANTITY, 1),
            }
            species_hint = (
                user_input.get(ATTR_SPECIES, "").strip() or self._crop_base[ATTR_NAME]
            )
            return await self._search_species(species_hint)

        return self.async_show_form(
            step_id="add_crop",
            data_schema=_CROP_SCHEMA,
            errors={},
        )

    def _opb_helper(self) -> OpenPlantbookHelper | None:
        """Return an OpenPlantbookHelper if credentials are configured."""
        client_id = self.config_entry.data.get(CONF_CLIENT_ID, "")
        secret = self.config_entry.data.get(CONF_CLIENT_SECRET, "")
        if client_id and secret:
            return OpenPlantbookHelper(client_id, secret)
        return None

    async def _search_species(self, hint: str) -> FlowResult:
        """Query OpenPlantbook and move to the selection step."""
        self._last_search_hint = hint
        options: list[selector.SelectOptionDict] = [
            selector.SelectOptionDict(value=_NO_SPECIES, label="— None —")
        ]
        helper = self._opb_helper()
        if helper:
            try:
                result = await helper.openplantbook_search(hint)
                if result:
                    for plant in result.get("results", []):
                        pid = plant.get(OPB_PID, "")
                        label = plant.get(OPB_DISPLAY_PID, pid)
                        LOGGER.debug("Fetched data: %s", plant)
                        if pid:
                            options.append(
                                selector.SelectOptionDict(value=pid, label=label)
                            )
            except Exception:  # noqa: BLE001
                LOGGER.warning("OpenPlantbook search failed for hint: %s", hint)

        self._species_options = options
        return await self.async_step_select_species()

    async def async_step_select_species(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user pick a species from OpenPlantbook search results."""
        if user_input is not None:
            refine = user_input.get("refine_search", "").strip()
            if refine:
                return await self._search_species(refine)

            pid = user_input.get(ATTR_SPECIES)
            if pid and pid != _NO_SPECIES:
                self._pending_species = pid
                self._pending_image_url = None
                helper = self._opb_helper()
                if helper:
                    try:
                        opb_result = await helper.openplantbook_get(pid)
                        if opb_result is not None:
                            self._pending_image_url = opb_result.get("image_url")
                    except Exception:  # noqa: BLE001
                        LOGGER.warning("OpenPlantbook get failed for pid: %s", pid)
            else:
                self._pending_species = None
                self._pending_image_url = None

            return await self.async_step_phases()

        schema = vol.Schema(
            {
                vol.Required(ATTR_SPECIES, default=_NO_SPECIES): (
                    selector.SelectSelector(
                        selector.SelectSelectorConfig(options=self._species_options)
                    )
                ),
                vol.Optional("refine_search"): selector.TextSelector(),
            }
        )
        opb_url = (
            "https://open.plantbook.io/browse-db/"
            f"?contain={quote(self._last_search_hint)}&scope=public"
        )
        return self.async_show_form(
            step_id="select_species",
            data_schema=schema,
            description_placeholders={
                "name": self._crop_base.get(ATTR_NAME, ""),
                "opb_url": opb_url,
            },
        )

    async def async_step_phases(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Collect optional lifecycle phase date ranges for the crop."""
        if user_input is not None:
            phases: dict[str, dict[str, str | None]] = {}
            for phase in CROP_PHASES:
                start = user_input.get(f"{phase}") or None
                if phase == PHASE_SOWING and start is None:
                    start = datetime.now(tz=UTC).date().isoformat()
                if start:
                    phases[phase] = {"start": start}
            return await self._save_crop(phases=phases)

        return self.async_show_form(
            step_id="phases",
            data_schema=_phases_schema(),
            description_placeholders={"name": self._crop_base.get(ATTR_NAME, "")},
        )

    async def _save_crop(self, phases: dict[str, dict[str, str | None]]) -> FlowResult:
        """Persist the new crop to the config entry and reload."""
        new_crop = {
            "id": str(uuid.uuid4()),
            **self._crop_base,
            ATTR_SPECIES: self._pending_species,
            "image_url": self._pending_image_url,
            "phases": phases,
        }
        existing_crops = list(self.config_entry.data.get(CONF_CROPS, []))
        existing_crops.append(new_crop)
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={**self.config_entry.data, CONF_CROPS: existing_crops},
        )
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        return self.async_create_entry(title="", data={})

    async def async_step_finish(
        self,
        user_input: dict[str, Any] | None = None,  # noqa: ARG002
    ) -> FlowResult:
        """Finish without adding a crop."""
        return self.async_create_entry(title="", data={})
