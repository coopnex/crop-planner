"""AI task entity for generating crop maintenance chore suggestions."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.ai_task import (
    AITaskEntity,
    AITaskEntityFeature,
    GenDataTask,
    GenDataTaskResult,
    async_generate_data,
)
from homeassistant.components.persistent_notification import async_create
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import async_generate_entity_id

from .ai_task_helpers import _build_context, _find_delegate_entity_id
from .const import (
    CHORE_CATEGORY_ICONS,
    CONF_CROPS,
    CONF_TODOS,
    COORDINATOR,
    DOMAIN,
    LOGGER,
    AIState,
    ChoreCategory,
)

if TYPE_CHECKING:
    from homeassistant.components.conversation import ChatLog
    from homeassistant.core import HomeAssistant

    from .coordinator import CropPlannerConfigEntry, CropPlannerCoordinator

_DEFAULT_INSTRUCTIONS = (
    "Analyse the context of a vegetable garden and suggest practical near-term "
    "(1 month) maintenance tasks for the gardener. "
    "Take into account the existing crops, the location and current time of year. "
    "Focus on watering, fertilising, pest inspection, pruning, and "
    "harvesting based on general knowledge. "
    "Generate task summaries and descriptions in the user's language. "
    "Propose also new recommended crops according to the current time of the year. "
    "Check existing tasks to avoid repetitions."
    "Return up to new 10 suggested tasks each time. "
    "Also return a short garden_summary (2-3 sentences) describing the current "
    "state of the garden and the most urgent priorities, in the user's language."
)

_SUGGESTION_SCHEMA = vol.Schema(
    {
        vol.Required("garden_summary"): str,
        vol.Required("tasks"): [
            vol.Schema(
                {
                    vol.Required("summary"): str,
                    vol.Optional("description"): str,
                    vol.Optional("due_date"): str,
                    vol.Optional("crop_name"): str,
                    vol.Optional("crop_entity_id"): str,
                    vol.Optional("category"): vol.In([c.value for c in ChoreCategory]),
                }
            )
        ],
    }
)


class GenerateChoresAITask(AITaskEntity):
    """
    AI task entity that generates crop maintenance todo suggestions.

    When invoked (e.g. via the ai_task.generate_data service), it:
    1. Enriches the task instructions with the current crop context.
    2. Delegates to another available AI task entity for LLM inference.
    3. Appends the returned suggestions to the crop chores todo list.
    """

    _attr_should_poll = False
    _attr_supported_features = AITaskEntityFeature.GENERATE_DATA
    _attr_has_entity_name = True
    _attr_translation_key = "generate_chores"

    def __init__(self, hass: HomeAssistant, entry: CropPlannerConfigEntry) -> None:
        """Initialise the entity."""
        coordinator: CropPlannerCoordinator = hass.data[DOMAIN][COORDINATOR]
        self._hass = hass
        self._entry = entry
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_generate_chores"
        self._device_id = coordinator.device_id
        self.entity_id = async_generate_entity_id(
            f"{Platform.AI_TASK}.{{}}", "crop generate chores", current_ids={}
        )

    async def _async_generate_data(
        self,
        task: GenDataTask,
        chat_log: ChatLog,  # noqa: ARG002
    ) -> GenDataTaskResult:
        """Enrich the task with crop context, delegate to an LLM, and add todos."""
        self._coordinator.set_ai_state(AIState.PROPOSING_TASKS)
        try:
            return await self._async_generate_data_inner(task)
        finally:
            self._coordinator.set_ai_state(AIState.IDLE)

    async def _async_generate_data_inner(self, task: GenDataTask) -> GenDataTaskResult:
        """Inner implementation of generate data."""
        crops: list[dict] = list(self._entry.data.get(CONF_CROPS, []))
        todos: list[dict] = list(self._entry.data.get(CONF_TODOS, []))

        delegate_entity_id = _find_delegate_entity_id(self._hass)
        if delegate_entity_id is None:
            msg = (
                "No AI task entity available to process the request. "
                "Set up an AI assistant integration (e.g. Google AI, OpenAI) first."
            )
            raise HomeAssistantError(msg)
        LOGGER.debug("self._hass= %s", self._hass)
        crop_context = _build_context(self._hass, crops, todos)
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
        data: dict = result.data or {}
        tasks: list[dict] = data.get("tasks", [])
        if tasks:
            self._add_todos(tasks)

        garden_summary: str = data.get("garden_summary", "")
        if garden_summary:
            task_lines = "\n".join(
                f"- {t.get('summary', '')}" for t in tasks if t.get("summary")
            )
            message = garden_summary
            if task_lines:
                message += f"\n\n{task_lines}"
            todo_entity_id = er.async_get(self._hass).async_get_entity_id(
                "todo", DOMAIN, f"{self._entry.entry_id}_todos"
            )
            if todo_entity_id:
                message += f"\n\n[📋](/todo?entity_id={todo_entity_id})"
            async_create(
                self._hass,
                message=message,
                title="🌱 Crop Planner",
                notification_id=f"{DOMAIN}_chore_suggestions",
            )

        return result

    def _add_todos(self, tasks: list[dict]) -> None:
        """Append AI-suggested tasks to the CONF_TODOS store and persist."""
        existing: list[dict] = list(self._entry.data.get(CONF_TODOS, []))
        for task in tasks:
            summary = task.get("summary", "").strip()
            if not summary:
                continue
            category = task.get("category", "")
            icon = CHORE_CATEGORY_ICONS.get(category, "")
            entry: dict = {
                "uid": str(uuid.uuid4()),
                "summary": f"{icon} {summary}" if icon else summary,
                "status": "needs_action",
                "due": task.get("due_date"),
                "description": task.get("description"),
            }
            if crop_entity_id := task.get("crop_entity_id"):
                entry["crop_entity_id"] = crop_entity_id
            if category:
                entry["category"] = category
            existing.append(entry)
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
