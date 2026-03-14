"""AI task platform — crop maintenance chore generation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components.ai_task import (
    AITaskEntity,
    AITaskEntityFeature,
    GenDataTask,
    GenDataTaskResult,
    async_generate_data,
)
from homeassistant.components.ai_task.const import DATA_COMPONENT
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import async_generate_entity_id

from .const import CONF_CROPS, COORDINATOR, CROP_PHASES, DOMAIN, LOGGER
from .todo import CONF_TODOS

if TYPE_CHECKING:
    from homeassistant.components.conversation import ChatLog
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import CropPlannerConfigEntry, CropPlannerCoordinator

_DEFAULT_INSTRUCTIONS = (
    "Analyse the context of a vegetable garden and suggest practical near-term "
    "(1 month) maintenance tasks for the gardener. "
    "Take into account the existing crops, the location and current time of year. "
    "Focus on watering, fertilising, pest inspection, pruning, and "
    "harvesting based on general knowledge. "
    "Generate task summaries and descriptions in the user's language. "
    "Propose also new recommended crops according to the current time of the year. "
    "Return between 5 to 10 of the most important tasks."
)

_SUGGESTION_SCHEMA = vol.Schema(
    {
        vol.Required("tasks"): [
            vol.Schema(
                {
                    vol.Required("summary"): str,
                    vol.Optional("description"): str,
                    vol.Optional("due_date"): str,
                    vol.Required("crop_name"): str,
                }
            )
        ]
    }
)


def _build_crop_context(crops: list[dict[str, Any]]) -> str:
    """Serialise current crop state into a human-readable block for the LLM."""
    today = datetime.now(tz=UTC).date().isoformat()
    lines = [f"* Today is {today}."]
    lines.append("* User language: spanish.")
    lines.append("* Location: near Barcelona (Spain).")
    lines.append("* Current crops:")
    for crop in crops:
        name = crop.get("name", "Unknown")
        species = crop.get("species") or "unspecified species"
        qty = crop.get("quantity", 1)
        phases: dict[str, dict] = crop.get("phases", {})
        phase_parts = []
        for phase in CROP_PHASES:
            if phase in phases:
                p = phases[phase]
                start = p.get("start", "")
                end = p.get("end", "")
                if start or end:
                    phase_parts.append(f"{phase}: {start or '?'} → {end or '?'}")
        phase_str = ", ".join(phase_parts) if phase_parts else "no phases set"
        lines.append(f"  - {name} ({species}), qty {qty}; phases: {phase_str}")
    return "\n".join(lines)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CropPlannerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the crop chores AI task entity."""
    async_add_entities([GenerateChoresAITask(hass, entry)])
    return True


class GenerateChoresAITask(AITaskEntity):
    """
    AI task entity that generates crop maintenance todo suggestions.

    When invoked (e.g. via the ai_task.generate_data service), it:
    1. Enriches the task instructions with the current crop context.
    2. Delegates to another available AI task entity for LLM inference.
    3. Appends the returned suggestions to the crop chores todo list.
    """

    _attr_supported_features = AITaskEntityFeature.GENERATE_DATA
    _attr_has_entity_name = True
    _attr_translation_key = "generate_chores"

    def __init__(self, hass: HomeAssistant, entry: CropPlannerConfigEntry) -> None:
        """Initialise the entity."""
        coordinator: CropPlannerCoordinator = hass.data[DOMAIN][COORDINATOR]
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_generate_chores"
        self._device_id = coordinator.device_id
        self.entity_id = async_generate_entity_id(
            f"{Platform.AI_TASK}.{{}}", "crop generate chores", current_ids={}
        )

    def _find_delegate_entity_id(self) -> str | None:
        """Return another ai_task entity that supports GENERATE_DATA, or None."""
        component = self._hass.data.get(DATA_COMPONENT)
        if component is None:
            return None
        for entity in component.entities:
            if (
                entity.entity_id != self.entity_id
                and AITaskEntityFeature.GENERATE_DATA in entity.supported_features
            ):
                return entity.entity_id
        return None

    async def _async_generate_data(
        self,
        task: GenDataTask,
        chat_log: ChatLog,  # noqa: ARG002
    ) -> GenDataTaskResult:
        """Enrich the task with crop context, delegate to an LLM, and add todos."""
        crops: list[dict] = list(self._entry.data.get(CONF_CROPS, []))
        if not crops:
            msg = "No crops are configured in the Crop Planner — nothing to suggest."
            raise HomeAssistantError(msg)

        delegate_entity_id = self._find_delegate_entity_id()
        if delegate_entity_id is None:
            msg = (
                "No AI task entity available to process the request. "
                "Set up an AI assistant integration (e.g. Google AI, OpenAI) first."
            )
            raise HomeAssistantError(msg)

        crop_context = _build_crop_context(crops)
        instructions = f"{_DEFAULT_INSTRUCTIONS}\n\nContext:\n{crop_context}"

        LOGGER.debug("Delegating crop chore generation to %s", delegate_entity_id)
        result = await async_generate_data(
            self._hass,
            task_name=task.name,
            entity_id=delegate_entity_id,
            instructions=instructions,
            structure=_SUGGESTION_SCHEMA,
        )
        LOGGER.debug("Received crop chore generation response: %s", result)
        tasks: list[dict] = (result.data or {}).get("tasks", [])
        if tasks:
            self._add_todos(tasks)

        return result

    def _add_todos(self, tasks: list[dict]) -> None:
        """Append AI-suggested tasks to the CONF_TODOS store and persist."""
        existing: list[dict] = list(self._entry.data.get(CONF_TODOS, []))
        for task in tasks:
            summary = task.get("summary", "").strip()
            if not summary:
                continue
            existing.append(
                {
                    "uid": str(uuid.uuid4()),
                    "summary": summary,
                    "status": "needs_action",
                    "due": task.get("due_date"),
                    "description": task.get("description"),
                }
            )
            LOGGER.debug("Adding suggested todo: %s", summary)

        self._hass.config_entries.async_update_entry(
            self._entry,
            data={**self._entry.data, CONF_TODOS: existing},
        )

    def update_registry(self) -> None:
        """Associate the entity with the integration device."""
        erreg = er.async_get(self._hass)
        erreg.async_update_entity(self.entity_id, device_id=self._device_id)

    async def async_added_to_hass(self) -> None:
        """Register in entity registry once added to hass."""
        self.update_registry()
