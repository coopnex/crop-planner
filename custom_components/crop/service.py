"""Service module handles the HA service call interface."""

from __future__ import annotations

import asyncio
import pathlib
import shutil
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import SERVICE_RELOAD, Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.service import async_register_admin_service

from .const import (
    ATTR_NAME,
    ATTR_QUANTITY,
    ATTR_SPECIES,
    CONF_CROPS,
    COORDINATOR,
    DOMAIN,
    LOGGER,
)
from .crop import CropData

if TYPE_CHECKING:
    from homeassistant.helpers.entity_component import EntityComponent

    from .coordinator import CropPlannerCoordinator, CropPlannerData


def _parse_dd_mmm(value: str) -> date | None:
    """Convert a date string in dd mmm format to a date object."""
    if isinstance(value, date):
        return value
    year = datetime.now(tz=UTC).year
    return datetime.strptime(f"{value} {year} +0000", "%d %b %Y %z").date()


RELOAD_SERVICE_SCHEMA = vol.Schema({})
CREATE_CROP_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Optional(ATTR_QUANTITY): cv.positive_int,
        vol.Optional(ATTR_SPECIES): cv.string,
    }
)
_component = None


def _resolve_ai_task_entity_id(hass: HomeAssistant, unique_id: str) -> str | None:
    """Return the entity_id for an ai_task entity with the given unique_id."""
    return er.async_get(hass).async_get_entity_id(Platform.AI_TASK, DOMAIN, unique_id)


async def _wait_for_reload(coordinator: CropPlannerCoordinator) -> bool:
    """
    Wait for the config entry to finish reloading after an update.

    Returns True if the entry returned to LOADED within the timeout, False otherwise.
    """
    entry = coordinator.config_entry
    # Wait up to 2 s for the reload to start (entry leaves LOADED state).
    for _ in range(20):
        if entry.state != ConfigEntryState.LOADED:
            break
        await asyncio.sleep(0.1)
    # Wait up to 10 s for the reload to finish (entry returns to LOADED).
    for _ in range(100):
        if entry.state == ConfigEntryState.LOADED:
            return True
        await asyncio.sleep(0.1)
    return False


async def _enrich_crop(
    hass: HomeAssistant,
    coordinator: CropPlannerCoordinator,
    crop_id: str,
    crop_name: str,
    species: str | None,
) -> None:
    """Run GuessSpecies and GeneratePlantImage AI tasks and patch the crop entry."""
    if not await _wait_for_reload(coordinator):
        LOGGER.warning(
            "Config entry did not return to LOADED state; skipping enrichment"
        )
        return

    entry = coordinator.config_entry
    fields: dict = {}

    # Step 1: guess species if not already provided.
    if not species:
        species = await invoke_guess_species_task(crop_name, entry, hass)
        if species:
            fields["species"] = species

    # Step 2: generate an AI image.
    signed_image_url = await invoke_image_generation_task(crop_name, entry, hass)
    if signed_image_url:
        url_path = urlparse(signed_image_url).path
        filename = pathlib.Path(url_path).name
        fields["image_url"] = f"/local/crop_planner/{filename}"

    # Step 3: fill remaining fields (phases etc.) — returns suggestions without
    # touching the config entry.
    phases = await invoke_enrich_crops_task(crop_id, entry, hass)
    if phases:
        fields["phases"] = phases

    # Single write at the end: merge all generated fields into the crop.
    if fields:
        _patch_crop(hass, coordinator, crop_id, fields)
    if signed_image_url:
        await hass.async_add_executor_job(_persist_image, hass, signed_image_url)


async def invoke_enrich_crops_task(
    crop_id: str, entry: ConfigEntry[CropPlannerData], hass: HomeAssistant
) -> dict | None:
    """Invoke the enrich_crop_data AI task and return phase suggestions for crop_id."""
    entity_id = _resolve_ai_task_entity_id(hass, f"{entry.entry_id}_enrich_crop_data")
    if not entity_id:
        LOGGER.debug("FillCropFieldsAITask entity not found; skipping field enrichment")
        return None
    try:
        from homeassistant.components.ai_task import (  # noqa: PLC0415
            async_generate_data,
        )

        result = await async_generate_data(
            hass,
            task_name="enrich_crop_data",
            entity_id=entity_id,
            instructions="",
        )
        LOGGER.debug("Enriched crop data for %s with result %r", crop_id, result)
        # Extract phase suggestions for this specific crop from the returned data.
        erreg = er.async_get(hass)
        for suggestion in (result.data or {}).get("crops", []):
            reg_entry = erreg.async_get(suggestion.get("entity_id", ""))
            if reg_entry and reg_entry.unique_id == crop_id:
                return suggestion.get("phases")
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("FillCropFieldsAITask failed for %s: %s", crop_id, exc)
    return None


async def invoke_image_generation_task(
    crop_name: str, entry: ConfigEntry[CropPlannerData], hass: HomeAssistant
) -> str | None:
    """Generate an AI plant image for the given crop name and return the URL."""
    image_query = crop_name
    entity_id = _resolve_ai_task_entity_id(
        hass, f"{entry.entry_id}_generate_plant_image"
    )
    if entity_id:
        try:
            from homeassistant.components.ai_task import (  # noqa: PLC0415
                async_generate_data,
            )

            result = await async_generate_data(
                hass,
                task_name="generate_plant_image",
                entity_id=entity_id,
                instructions=image_query,
            )
            image_url: str | None = (result.data or {}).get("image_url")
            LOGGER.debug("Generated image for %r: %s", image_query, image_url)
            if image_url:
                return image_url
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning(
                "GeneratePlantImageAITask failed for %r: %s", image_query, exc
            )
    else:
        LOGGER.debug(
            "GeneratePlantImageAITask entity not found; skipping image generation"
        )
        return None


def _persist_image(hass: HomeAssistant, signed_url: str) -> str:
    """
    Copy the generated image to www/crop_planner/ and return the destination filename.

    Runs in an executor thread because it performs blocking file I/O.
    """
    url_path = urlparse(signed_url).path
    rel_path = url_path.lstrip("/")
    src = pathlib.Path(hass.config.media_dirs["local"])  / rel_path
    dst_dir = pathlib.Path(hass.config.config_dir) / "www" / "crop_planner"
    dst_dir.mkdir(parents=True, exist_ok=True)
    filename = pathlib.Path(rel_path).name
    shutil.copy2(src, dst_dir / filename)
    return filename


async def invoke_guess_species_task(
    crop_name: str, entry: ConfigEntry[CropPlannerData], hass: HomeAssistant
) -> str | None:
    """Guess the botanical species for the given crop name and return it."""
    entity_id = _resolve_ai_task_entity_id(hass, f"{entry.entry_id}_guess_species")
    if entity_id:
        try:
            from homeassistant.components.ai_task import (  # noqa: PLC0415
                async_generate_data,
            )

            result = await async_generate_data(
                hass,
                task_name="guess_species",
                entity_id=entity_id,
                instructions=crop_name,
            )
            species = (result.data or {}).get("species")
            LOGGER.debug("Guessed species for %r: %s", crop_name, species)
            if species:
                return species
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("GuessSpeciesAITask failed for %r: %s", crop_name, exc)
    else:
        LOGGER.debug("GuessSpeciesAITask entity not found; skipping species guess")
        return None


def _patch_crop(
    hass: HomeAssistant,
    coordinator: CropPlannerCoordinator,
    crop_id: str,
    fields: dict,
) -> None:
    """Merge *fields* into the crop with the given id and persist to config entry."""
    entry = coordinator.config_entry
    crops = [
        {**c, **fields} if c.get("id") == crop_id else c
        for c in entry.data.get(CONF_CROPS, [])
    ]
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_CROPS: crops}
    )


def register_component_services(component: EntityComponent) -> None:
    """Register the component."""
    _component = component

    @callback
    async def reload_service_handler(call: ServiceCall) -> None:  # noqa: ARG001
        """Reload yaml entities."""
        conf = await _component.async_prepare_reload(skip_reset=True)
        if conf is None or conf == {}:
            conf = {DOMAIN: {}}

    @callback
    async def create_crop(call: ServiceCall) -> None:
        """Create a new crop entry and enrich it with AI-derived species and image."""
        hass = call.hass
        coordinator: CropPlannerCoordinator = hass.data[DOMAIN][COORDINATOR]
        name_: str = call.data[ATTR_NAME]
        crop_data = CropData(
            id=call.context.id,
            name=name_.capitalize(),
            quantity=call.data.get(ATTR_QUANTITY, 1),
            species=call.data.get(ATTR_SPECIES, None),
        )

        new_data = {
            **coordinator.config_entry.data,
            CONF_CROPS: [
                *coordinator.config_entry.data.get(CONF_CROPS, []),
                crop_data.__dict__,
            ],
        }
        hass.config_entries.async_update_entry(
            coordinator.config_entry, data=new_data, unique_id=call.context.id
        )
        hass.async_create_task(
            _enrich_crop(
                hass, coordinator, crop_data.id, crop_data.name, crop_data.species
            )
        )

    async_register_admin_service(
        _component.hass,
        DOMAIN,
        SERVICE_RELOAD,
        reload_service_handler,
        schema=RELOAD_SERVICE_SCHEMA,
    )

    component.hass.services.async_register(
        DOMAIN,
        "create_crop",
        create_crop,
        CREATE_CROP_SCHEMA,
    )
