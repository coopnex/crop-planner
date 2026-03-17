"""Sensor platform — AI task state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import Platform
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import AIState, COORDINATOR, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import CropPlannerConfigEntry, CropPlannerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CropPlannerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the AI state sensor."""
    coordinator: CropPlannerCoordinator = hass.data[DOMAIN][COORDINATOR]
    async_add_entities([AIStateSensor(hass, entry, coordinator)])
    return True


class AIStateSensor(CoordinatorEntity, SensorEntity):
    """Sensor that exposes the current AI task state as a human-readable string."""

    _attr_has_entity_name = True
    _attr_translation_key = "ai_state"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: CropPlannerConfigEntry,
        coordinator: CropPlannerCoordinator,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_ai_state"
        self._device_id = coordinator.device_id
        self.entity_id = async_generate_entity_id(
            f"{Platform.SENSOR}.{{}}", "crop ai state", current_ids={}
        )

    @property
    def native_value(self) -> str:
        """Return the current AI state."""
        return self.coordinator.ai_state

    def update_registry(self) -> None:
        """Associate the entity with the integration device."""
        erreg = er.async_get(self._hass)
        erreg.async_update_entity(self.entity_id, device_id=self._device_id)

    async def async_added_to_hass(self) -> None:
        """Register in entity registry once added to hass."""
        await super().async_added_to_hass()
        self.update_registry()
