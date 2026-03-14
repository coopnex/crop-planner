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

from .const import CONF_CROPS, COORDINATOR, DOMAIN, PHASE_ICONS
from .coordinator import (
    CropPlannerConfigEntry,
    CropPlannerCoordinator,
)
from .data import create_crop_data
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

        for crop_dict in self._entry.data.get(CONF_CROPS, []):
            try:
                crop = create_crop_data(crop_dict)
            except Exception:  # noqa: BLE001, S112
                continue

            for phase_name, phase in crop.phases.items():
                if phase.start is None:
                    continue
                phase_end = phase.end
                if phase.end is None:
                    phase_end = phase.start + datetime.timedelta(days=1)
                if not (window_start <= phase.start <= window_end):
                    continue
                icon = PHASE_ICONS.get(phase_name, "📅")
                summary = f"{icon} {crop.name} — {phase_name.capitalize()}"
                events.append(
                    CalendarEvent(
                        start=phase.start,
                        end=phase_end,
                        summary=summary,
                    )
                )

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
                    summary=f"☑ {todo.get('summary', '')}",
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
