"""Example of a custom component exposing a service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.loader import async_get_loaded_integration

from .const import COMPONENT, COORDINATOR, CROP_PLATFORM, DOMAIN, LOGGER
from .coordinator import (
    CropPlannerConfigEntry,
    CropPlannerCoordinator,
    CropPlannerData,
)
from .crop import Crop
from .data import create_crop_data
from .service import register_component_services

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.core_config import Config
    from homeassistant.helpers.typing import ConfigType

PLATFORMS: list[Platform] = [Platform.CALENDAR]


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Your controller/hub specific code."""
    # Data that you want to share with your platforms

    load_platform(hass, DOMAIN, CROP_PLATFORM, {}, config)

    return True


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up this integration using YAML."""
    hass.data[DOMAIN] = {}
    hass.data.setdefault(DOMAIN, {})
    component = EntityComponent(LOGGER, DOMAIN, hass)
    hass.data[DOMAIN][COMPONENT] = component
    register_component_services(component)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CropPlannerConfigEntry) -> bool:
    """Set up this integration using UI."""
    coordinator = CropPlannerCoordinator(hass=hass, config_entry=entry, logger=LOGGER)
    entry.runtime_data = CropPlannerData(
        integration=async_get_loaded_integration(hass, entry.domain),
        crops=[],
        coordinator=coordinator,
    )
    hass.data[DOMAIN][COORDINATOR] = coordinator
    coordinator.update_registry()

    await coordinator.async_config_entry_first_refresh()

    crops = [
        Crop(hass, create_crop_data(crop_data))
        for crop_data in entry.data.get("crops", [])
    ]
    LOGGER.info("Setting up crops: %s", crops)

    component = hass.data[DOMAIN][COMPONENT]
    await component.async_add_entities(crops)
    entry.runtime_data.crops = crops

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


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
