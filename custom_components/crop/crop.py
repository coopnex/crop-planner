"""
Crop Planner integration: entities and data structures for crops.

This module provides the CropData dataclass and the Crop Entity used by the
Crop Planner Home Assistant integration to represent planted crops, their
quantities, and device/entity registration behavior.
"""

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import STATE_OK, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.entity import (
    Entity,
    async_generate_entity_id,
)

from custom_components.crop.data import (
    CropData,
)

from .const import (
    COORDINATOR,
    CROP_PLATFORM,
    DOMAIN,
    ICON,
)

if TYPE_CHECKING:
    from .coordinator import CropPlannerCoordinator


class Crop(Entity):
    """Class to represent a crop."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, hass: HomeAssistant, config: CropData) -> None:
        """Initialize a crop with a name, planting date, and harvest date."""
        coordinator: CropPlannerCoordinator = hass.data[DOMAIN][COORDINATOR]
        self._hass = hass
        self._name = config.name
        self._quantity = config.quantity
        self._sowing_date = config.sowing_date
        self._species = config.species
        if config.image_url is not None:
            self._attr_entity_picture = config.image_url
        else:
            self._attr_entity_picture = "/local/crop_planner/default.jpg"
        self._config_entries = []
        self._unique_id = config.id
        self._attr_unique_id = self._unique_id
        self._device_id = coordinator.device_id
        self.entity_id = async_generate_entity_id(
            f"{CROP_PLATFORM}.{{}}", self._name, current_ids={}
        )
        self._attr_icon = ICON
        self._attr_state = STATE_OK

    @property
    def name(self) -> str:
        """Return the name of the crop."""
        return self._name

    @property
    def quantity(self) -> int:
        """Return the quantity of the crop."""
        return self._quantity

    @property
    def device_id(self) -> str | None:
        """The device ID used for all the entities."""
        return self._device_id

    @property
    def extra_state_attributes(self) -> dict:
        """Return the device specific state attributes."""
        return {
            "name": self._name,
            "quantity": self._quantity,
            "sowing_date": self._sowing_date,
            "species": self._species,
        }

    def update(self) -> None:
        """Run on every update of the entities."""
        new_state = STATE_OK
        self._attr_state = new_state

    def update_registry(self) -> None:
        """Update registry with correct data."""
        erreg = er.async_get(self._hass)
        erreg.async_update_entity(self.entity_id, device_id=self.device_id)

    async def async_added_to_hass(self) -> None:
        self.update_registry()
