"""Example of a custom component exposing a service."""

from __future__ import annotations
from poplib import CR
from typing import List

from crop_planner.crop import Crop
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.core_config import Config
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.discovery import async_load_platform, load_platform
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_loaded_integration

from .const import ATTR_CROP, COMPONENT, COORDINATOR, CROP_PLATFORM, DOMAIN, LOGGER
from .coordinator import CropPlannerConfigEntry, CropPlannerCoordinator, CropPlannerData
from .data import CropData, create_crop_data
from .service import register_component_services

PLATFORMS: list[Platform] = [Platform.CALENDAR]


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Your controller/hub specific code."""
    # Data that you want to share with your platforms

    load_platform(hass, "crop", DOMAIN, {}, config)

    return True


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CropPlannerConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data[DOMAIN] = {}
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})

    coordinator = CropPlannerCoordinator(hass=hass, config_entry=entry, logger=LOGGER)
    entry.runtime_data = CropPlannerData(
        integration=async_get_loaded_integration(hass, entry.domain),
        crops=[],
        coordinator=coordinator,
    )
    hass.data[DOMAIN][COORDINATOR] = coordinator
    coordinator.update_registry()

    component = EntityComponent(LOGGER, DOMAIN, hass)
    hass.data[DOMAIN][COMPONENT] = component
    register_component_services(component, coordinator)

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    crops = []
    crop_datas: list[dict] = entry.data.get("crops", [])
    for crop_data in crop_datas:
        LOGGER.info("Setting up crop: %s", crop_data)
        crops.append(
            Crop(
                hass,
                CropData(
                    id=crop_data["id"],
                    name=crop_data["name"],
                    quantity=crop_data["quantity"],
                ),
            )
        )

    entry.runtime_data.crops = crops
    LOGGER.info("Setting up crops: %s", crops)
    await component.async_add_entities(crops)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # await _add_to_device_registry(hass, [], coordinator.device_id)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def _add_to_device_registry(
    hass: HomeAssistant, entities: list[Entity], device_id: str
) -> None:
    """Add all related entities to the correct device_id"""

    erreg = er.async_get(hass)
    for entity in entities:
        erreg.async_update_entity(entity.registry_entry.entity_id, device_id=device_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: CropPlannerConfigEntry
) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    for crop in entry.runtime_data.crops:
        LOGGER.info("Unloading crop: %s", crop)

    erreg = er.async_get(hass)
    for entity in entry.runtime_data.crops:
        if entity.registry_entry is not None:
            erreg.async_remove(entity.registry_entry.entity_id)
    entry.async_create_task(
        hass, hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    )
    return True


async def async_reload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
