"""
Crop Planner integration: entities and data structures for crops.

This module provides the CropData dataclass and the Crop Entity used by the
Crop Planner Home Assistant integration to represent planted crops, their
quantities, and device/entity registration behavior.
"""

from collections import OrderedDict
from dataclasses import dataclass

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_PICTURE,
    ATTR_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_OK,
    STATE_PROBLEM,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    EntityCategory,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.core_config import Config
from homeassistant.helpers import (
    config_validation as cv,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import (
    Entity,
    async_generate_entity_id,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from crop_planner.coordinator import CropPlannerConfigEntry
from custom_components.crop_planner.data import (
    CropData,
)

from .const import (
    ATTR_QUANTITY,
    COMPONENT,
    CONF_CROPS,
    COORDINATOR,
    CROP_PLANNER,
    CROP_PLATFORM,
    DOMAIN,
    ICON,
    LOGGER,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CropPlannerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up this integration using UI."""
    crops = [Crop(hass, cropData) for cropData in entry.data.get("crops", [])]
    LOGGER.info("Setting up crops: %s", crops)
    # async_add_entities(crops)
    return True


class Crop(Entity):
    """Class to represent a crop."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass: HomeAssistant, config: CropData) -> None:
        """Initialize a crop with a name, planting date, and harvest date."""
        self._hass = hass
        self._name = config.name
        self._quantity = config.quantity
        self._config_entries = []
        self._unique_id = config.id
        self._attr_unique_id = self._unique_id
        self._device_id = self._unique_id
        self.entity_id = async_generate_entity_id(
            f"{CROP_PLATFORM}.{{}}", self._name, current_ids={}
        )
        self._attr_icon = ICON
        self._attr_state = STATE_OK
        self.sowing_date = None

    @property
    def name(self) -> str:
        """Return the name of the crop."""
        return self._name

    @property
    def quantity(self) -> int:
        """Return the quantity of the crop."""
        return self._quantity

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def device_class(self):
        return DOMAIN

    @property
    def device_id(self) -> str:
        """The device ID used for all the entities"""
        return self._device_id

    @property
    def extra_state_attributes(self) -> dict:
        """Return the device specific state attributes."""
        attributes = {"name": self._name, "quantity": self._quantity}
        return attributes

    def update(self) -> None:
        """Run on every update of the entities"""

        new_state = STATE_OK
        self._attr_state = new_state
        self.update_registry()

    def update_registry(self) -> None:
        """Update registry with correct data."""
        # Is there a better way to add an entity to the device registry?
        # coordinator = self._hass.data[DOMAIN][COORDINATOR]
        # erreg = er.async_get(self._hass)
        # erreg.async_update_entity(
        #     self.registry_entry.entity_id, device_id=coordinator.device_id
        # )
        # device_registry.async_get_or_create(
        #     config_entry_id=coordinator.config_entry.entry_id,
        #     identifiers={(DOMAIN, self.unique_id)},
        #     name=self.name,
        #     model="Crop Planner",
        #     manufacturer="Crop Planner",
        # )
        # if self.device_id is None:
        #     device = device_registry.async_get_device(
        #         identifiers={(DOMAIN, self.unique_id)}
        #     )
        #     if device is not None:
        #         self._device_id = device.id

    @property
    def options_entities(self) -> list[Entity]:
        """List all threshold entities."""
        return []

    async def async_added_to_hass(self) -> None:
        self.update_registry()
