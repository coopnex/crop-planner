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

from .const import COORDINATOR, DOMAIN
from .coordinator import (
    CropPlannerConfigEntry,
    CropPlannerCoordinator,
)
from .todo import CONF_TODOS


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

    _attr_has_entity_name = True
    _attr_translation_key = "crop_calendar"

    def __init__(self, hass: HomeAssistant, entry: CropPlannerConfigEntry) -> None:
        """Initialize the CropPlannerCalendar entity."""
        coordinator: CropPlannerCoordinator = hass.data[DOMAIN][COORDINATOR]
        self._hass = hass
        self._entry = entry
        self._config_entries = []
        self._unique_id = f"{entry.entry_id}_calendar"
        self._attr_unique_id = self._unique_id
        self._device_id = coordinator.device_id
        self.entity_id = async_generate_entity_id(
            f"{Platform.CALENDAR}.{{}}", "Crop calendar", current_ids={}
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        events: list[CalendarEvent] = []
        window_start = start_date.date()
        window_end = end_date.date()

        for todo in self._entry.data.get(CONF_TODOS, []):
            if todo.get("status") == "completed":
                continue
            due_str = todo.get("due")
            if not due_str:
                continue
            try:
                due = datetime.date.fromisoformat(due_str)
            except ValueError:
                continue
            if not (window_start <= due <= window_end):
                continue
            events.append(
                CalendarEvent(
                    start=due,
                    end=due + datetime.timedelta(days=1),
                    summary=todo.get("summary", ""),
                    description=todo.get("description"),
                )
            )

        return events

    def update_registry(self) -> None:
        """Update registry with correct data."""
        erreg = er.async_get(self._hass)
        erreg.async_update_entity(self.entity_id, device_id=self._device_id)

    async def async_added_to_hass(self) -> None:
        """Register the entity in the entity registry once added to hass."""
        self.update_registry()
