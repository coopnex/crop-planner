"""AI task platform — registers all crop AI task entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .ai_task_chores import GenerateChoresAITask
from .ai_task_fill_fields import FillCropFieldsAITask
from .ai_task_image import GeneratePlantImageAITask
from .ai_task_species import GuessSpeciesAITask

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import CropPlannerConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CropPlannerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the crop AI task entities."""
    async_add_entities(
        [
            GenerateChoresAITask(hass, entry),
            FillCropFieldsAITask(hass, entry),
            GuessSpeciesAITask(hass, entry),
            GeneratePlantImageAITask(hass, entry),
        ]
    )
    return True
