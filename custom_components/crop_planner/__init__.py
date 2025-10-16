"""Example of a custom component exposing a service."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.core_config import Config
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_loaded_integration

from custom_components.crop_planner.coordinator import CropPlannerCoordinator
from custom_components.crop_planner.data import CropPlannerConfigEntry, CropPlannerData

from .const import ATTR_CROP, COMPONENT, COORDINATOR, DOMAIN, LOGGER

PLATFORMS = []


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the sync service example component."""

    # def create_crop(call: ServiceCall) -> None:
    #     """My first service."""
    #     LOGGER.info("Received data", call.data)

    # # Register our service with Home Assistant.
    # hass.services.register(DOMAIN, "create_crop", create_crop)

    # Return boolean to indicate that initialization was successfully.
    return True


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML."""
    return True


PLATFORMS: list[Platform] = []


async def async_setup_entry(hass: HomeAssistant, entry: CropPlannerConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data[DOMAIN] = {}
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})

    coordinator = CropPlannerCoordinator(hass=hass, config_entry=entry, logger=LOGGER)
    entry.runtime_data = CropPlannerData(
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )
    hass.data[DOMAIN][COORDINATOR] = coordinator

    component = EntityComponent(LOGGER, DOMAIN, hass)
    # hass.data[DOMAIN][COMPONENT] = component
    # register_component_services(component, coordinator)

    # cropPlanner = CropPlanner(hass, entry)
    # hass.data[DOMAIN][entry.entry_id] = cropPlanner

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # component = hass.data[DOMAIN][COMPONENT]
    # await component.async_add_entities([coordinator])

    await _add_to_device_registry(hass, [], coordinator.device_id)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def _add_to_device_registry(
    hass: HomeAssistant, entities: list[Entity], device_id: str
) -> None:
    """Add all related entities to the correct device_id"""

    # There must be a better way to do this, but I just can't find a way to set the
    # device_id when adding the entities.
    erreg = er.async_get(hass)
    for entity in entities:
        erreg.async_update_entity(entity.registry_entry.entity_id, device_id=device_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
