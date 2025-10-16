"""DataUpdateCoordinator for integration_blueprint."""

from __future__ import annotations

from logging import Logger
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import (
    config_validation as cv,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import ATTR_CROP, COMPONENT, COORDINATOR, DOMAIN, LOGGER

if TYPE_CHECKING:
    from .data import CropPlannerConfigEntry


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class CropPlannerCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: CropPlannerConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: CropPlannerConfigEntry, logger: Logger) -> None:
        super().__init__(
            hass,
            logger = logger,
            name="Crop Planner",
            update_interval=None,
        )
        self._hass = hass
        self._config = config_entry
        self._name = "Crop Planner"
        self._attr_unique_id = self.config_entry.entry_id
        self._config_entries = []
        self._device_id = self.config_entry.entry_id
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}", self._name, current_ids={}
        )

    @property
    def unique_id(self) -> str:
        return self._attr_unique_id

    @property
    def device_id(self) -> str:
        """The device ID used for all the entities."""
        return self._device_id

    @property
    def device_info(self) -> dict:
        """Device info for devices."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "config_entries": self._config_entries,
            "model": self.name,
            "manufacturer": "Crop Planner",
        }


    def update_registry(self) -> None:
        """Update registry with correct data."""
        # Is there a better way to add an entity to the device registry?

        device_registry = dr.async_get(self._hass)
        device_registry.async_get_or_create(
            config_entry_id=self._config.entry_id,
            identifiers={(DOMAIN, self.unique_id)},
            name=self.name,
            model="Crop Planner",
            manufacturer="Crop Planner",
        )
        if self._device_id is None:
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, self.unique_id)}
            )
            self._device_id = device.id

    async def _async_update_data(self) -> Any:
        """Update data via library."""

