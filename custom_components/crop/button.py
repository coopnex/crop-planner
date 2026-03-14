"""Button platform — trigger the crop maintenance AI task."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.ai_task import async_generate_data
from homeassistant.components.button import ButtonEntity
from homeassistant.const import Platform
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import async_generate_entity_id

from .const import COORDINATOR, DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import CropPlannerConfigEntry, CropPlannerCoordinator

_AI_TASK_UNIQUE_ID_SUFFIX = "_generate_chores"
_AI_TASK_NAME = "crop_maintenance_suggestions"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CropPlannerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the crop maintenance suggestion button."""
    async_add_entities([GenerateChoresButton(hass, entry)])
    return True


class GenerateChoresButton(ButtonEntity):
    """Button that triggers the GenerateChoresAITask entity."""

    _attr_has_entity_name = True
    _attr_translation_key = "generate_chores"

    def __init__(self, hass: HomeAssistant, entry: CropPlannerConfigEntry) -> None:
        """Initialise the button."""
        coordinator: CropPlannerCoordinator = hass.data[DOMAIN][COORDINATOR]
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_generate_chores_button"
        self._device_id = coordinator.device_id
        self.entity_id = async_generate_entity_id(
            f"{Platform.BUTTON}.{{}}", "crop generate chores", current_ids={}
        )

    def _ai_task_entity_id(self) -> str | None:
        """Resolve the entity_id of our GenerateChoresAITask."""
        entity_registry = er.async_get(self._hass)
        return entity_registry.async_get_entity_id(
            Platform.AI_TASK,
            DOMAIN,
            f"{self._entry.entry_id}{_AI_TASK_UNIQUE_ID_SUFFIX}",
        )

    async def async_press(self) -> None:
        """Trigger the AI task to generate crop maintenance suggestions."""
        ai_entity_id = self._ai_task_entity_id()
        if ai_entity_id is None:
            LOGGER.error(
                "GenerateChoresAITask entity not found — cannot generate suggestions"
            )
            return
        LOGGER.debug("Triggering crop chore generation via %s", ai_entity_id)
        await async_generate_data(
            self._hass,
            task_name=_AI_TASK_NAME,
            entity_id=ai_entity_id,
            instructions="",
        )

    def update_registry(self) -> None:
        """Associate the entity with the integration device."""
        erreg = er.async_get(self._hass)
        erreg.async_update_entity(self.entity_id, device_id=self._device_id)

    async def async_added_to_hass(self) -> None:
        """Register in the entity registry once added to hass."""
        self.update_registry()
