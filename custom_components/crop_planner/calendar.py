"""
Calendar platform for the Crop Planner integration.

This module sets up calendar entities for the Crop Planner integration using
the CropPlannerCoordinator and related data types.
"""

import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from crop_planner.const import COORDINATOR, DOMAIN
from custom_components.crop_planner.coordinator import (
    CropPlannerConfigEntry,
    CropPlannerCoordinator,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CropPlannerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up this integration using UI."""
    async_add_entities([CropPlannerCalendar(hass, entry)])
    return True


class CropPlannerCalendar(CalendarEntity):
    """Representation of a Sensor."""

    _attr_name = "Crop Calendar"

    def __init__(self, hass: HomeAssistant, entry: CropPlannerConfigEntry) -> None:
        """Initialize the CropPlannerCalendar entity."""
        coordinator: CropPlannerCoordinator = hass.data[DOMAIN][COORDINATOR]
        self._hass = hass
        self._config_entries = []
        self._unique_id = f"{entry.entry_id}_calendar"
        self._attr_unique_id = self._unique_id
        self._device_id = coordinator.device_id
        self.entity_id = async_generate_entity_id(
            f"{Platform.CALENDAR}.{{}}", self._attr_name, current_ids={}
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        return []

    def update_registry(self) -> None:
        """Update registry with correct data."""
        erreg = er.async_get(self._hass)
        erreg.async_update_entity(self.entity_id, device_id=self._device_id)

    async def async_added_to_hass(self) -> None:
        self.update_registry()
