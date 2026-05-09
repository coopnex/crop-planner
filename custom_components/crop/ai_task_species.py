"""AI task entity for guessing the botanical species of a plant."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.ai_task import (
    AITaskEntity,
    AITaskEntityFeature,
    GenDataTask,
    GenDataTaskResult,
    async_generate_data,
)
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import async_generate_entity_id

from .ai_task_helpers import _find_delegate_entity_id
from .const import COORDINATOR, DOMAIN, LOGGER, AIState

if TYPE_CHECKING:
    from homeassistant.components.conversation import ChatLog
    from homeassistant.core import HomeAssistant

    from .coordinator import CropPlannerConfigEntry, CropPlannerCoordinator

_GUESS_SPECIES_INSTRUCTIONS = (
    "You are an expert botanist and horticulturist. "
    "Given a plant name provided by the user (which may be a common name, a local "
    "name, or a partial name), identify the most likely species. "
    "Take into account the user's location and climate when disambiguating between "
    "species — prefer varieties commonly grown in that region. "
    "Return the best-matching botanical species name (genus + species), the common "
    "English name, a confidence level ('high', 'medium', or 'low'), and a short "
    "note explaining the match or any ambiguity. "
    "If multiple species are plausible, pick the most common edible/garden variety "
    "for the given location and mention the alternatives in the notes field."
)

_GUESS_SPECIES_SCHEMA = vol.Schema(
    {
        vol.Required("species"): str,
        vol.Required("common_name"): str,
        vol.Required("confidence"): vol.In(["high", "medium", "low"]),
        vol.Optional("notes"): str,
    }
)


class GuessSpeciesAITask(AITaskEntity):
    """AI task entity that guesses the botanical species for a given plant name."""

    _attr_supported_features = AITaskEntityFeature.GENERATE_DATA
    _attr_has_entity_name = True
    _attr_translation_key = "guess_species"

    def __init__(self, hass: HomeAssistant, entry: CropPlannerConfigEntry) -> None:
        """Initialise the entity."""
        coordinator: CropPlannerCoordinator = hass.data[DOMAIN][COORDINATOR]
        self._hass = hass
        self._entry = entry
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_guess_species"
        self._device_id = coordinator.device_id
        self.entity_id = async_generate_entity_id(
            f"{Platform.AI_TASK}.{{}}", "guess species", current_ids={}
        )

    async def _async_generate_data(
        self,
        task: GenDataTask,
        chat_log: ChatLog,  # noqa: ARG002
    ) -> GenDataTaskResult:
        """Guess the species for the plant name given in task.instructions."""
        plant_name = (task.instructions or "").strip()
        if not plant_name:
            msg = "No plant name provided. Pass it via the instructions field."
            raise HomeAssistantError(msg)

        self._coordinator.set_ai_state(AIState.GUESSING_SPECIES)
        try:
            result = await self._inner_guess_species(plant_name, task)
            LOGGER.debug("Species guess result for %r: %s", plant_name, result.data)
            return result
        finally:
            self._coordinator.set_ai_state(AIState.IDLE)

    async def _inner_guess_species(
        self, plant_name: str, task: GenDataTask
    ) -> GenDataTaskResult:
        """Delegate species guessing to the LLM and return the result."""
        delegate_entity_id = _find_delegate_entity_id(self._hass)
        if delegate_entity_id is None:
            msg = (
                "No AI task entity available to process the request. "
                "Set up an AI assistant integration (e.g. Google AI, OpenAI) first."
            )
            raise HomeAssistantError(msg)
        latitude = self._hass.config.latitude
        longitude = self._hass.config.longitude
        context = (
            f"Plant name: {plant_name}\n"
            f"Location: latitude {latitude:.4f}, longitude {longitude:.4f}"
        )
        instructions = f"{_GUESS_SPECIES_INSTRUCTIONS}\n\n{context}"
        LOGGER.debug("Guessing species for %r via %s", plant_name, delegate_entity_id)
        return await async_generate_data(
            self._hass,
            task_name=task.name,
            entity_id=delegate_entity_id,
            instructions=instructions,
            structure=_GUESS_SPECIES_SCHEMA,
        )

    def update_registry(self) -> None:
        """Associate the entity with the integration device."""
        erreg = er.async_get(self._hass)
        erreg.async_update_entity(self.entity_id, device_id=self._device_id)

    async def async_added_to_hass(self) -> None:
        """Register in entity registry once added to hass."""
        self.update_registry()
