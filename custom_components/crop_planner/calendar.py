"""
Calendar platform for the Crop Planner integration.

This module sets up calendar entities for the Crop Planner integration using
the CropPlannerCoordinator and related data types.
"""

import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from crop_planner.const import LOGGER
from custom_components.crop_planner.coordinator import (
    CropPlannerConfigEntry,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CropPlannerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up this integration using UI."""
    LOGGER.info("Setting up calendar: %s", entry.data)
    async_add_entities([CropPlannerCalendar()])
    return True


class CropPlannerCalendar(CalendarEntity):
    """Representation of a Sensor."""

    _attr_name = "Crop Calendar"
    _attr_unique_id = "crop_calendar_1"

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
