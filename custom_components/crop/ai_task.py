"""AI task platform — crop maintenance chore generation and field filling."""

from __future__ import annotations

import copy
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
from homeassistant.components.persistent_notification import async_create
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import async_generate_entity_id

from .const import (
    CHORE_CATEGORY_ICONS,
    CONF_CROPS,
    CONF_TODOS,
    COORDINATOR,
    CROP_PHASES,
    CROP_PLATFORM,
    DOMAIN,
    LOGGER,
    ChoreCategory,
)

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


def _build_context(
    hass: HomeAssistant, crops: list[dict[str, Any]], todos: list[dict[str, Any]]
) -> str:
    """Serialise current crop state into a human-readable block for the LLM."""
    today = datetime.now(tz=UTC).date().isoformat()
    language = hass.config.language
    latitude = hass.config.latitude
    longitude = hass.config.longitude
    entity_registry = er.async_get(hass)
    lines = [f"* Today is {today}."]
    lines.append(f"* User language: {language}.")
    lines.append(f"* Location: (latitude {latitude:.4f}, longitude {longitude:.4f}).")
    if crops:
        lines.append("* Current crops:")
        for crop in crops:
            entity_id = entity_registry.async_get_entity_id(
                CROP_PLATFORM, DOMAIN, crop["id"]
            )
            line = _build_crop_context(crop, entity_id)
            lines.append(f"  - {line}")
    if todos:
        lines.append("* Current todos:")
        for todo in todos:
            summary = todo.get("summary")
            description = f"({todo.get('description') or ''})"
            lines.append(f"  - {summary} {description}")

    return "\n".join(lines)


def _build_crop_context(crop: dict[str, Any], entity_id: str | None = None) -> str:
    name = crop.get("name", "Unknown")
    species = crop.get("species") or None
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
    species_str = f" ({species})" if species else ""
    entity_str = f"; entity_id: {entity_id}" if entity_id else ""
    phase_str = f"; phases: {', '.join(phase_parts)}" if phase_parts else ""
    return f"{name}{species_str}: qty {qty}{entity_str}{phase_str}"


_FILL_FIELDS_INSTRUCTIONS = (
    "You are an expert horticulturist. "
    "For each crop listed in the context that is missing a species or has incomplete "
    "phase dates, fill in the blanks using your knowledge of the plant and the "
    "gardener's location and current date. "
    "Rules:\n"
    "- If species is missing, infer the most likely botanical or common species name "
    "  from the crop name and context.\n"
    "- For each phase (sowing, germination, flowering, harvest) that lacks a start "
    "  or end date, estimate sensible dates based on the species, climate of the "
    "  location, and any existing dates already recorded for that crop.\n"
    "- Only fill in fields that are genuinely missing; never overwrite existing values.\n"
    "- Return ONLY crops that actually need changes; omit crops that are already "
    "  complete.\n"
    "- Express all dates as ISO-8601 strings (YYYY-MM-DD)."
)

_PHASE_SCHEMA = vol.Schema(
    {
        vol.Optional("start"): vol.Any(str, None),
        vol.Optional("end"): vol.Any(str, None),
    }
)

_FILL_FIELDS_SCHEMA = vol.Schema(
    {
        vol.Required("crops"): [
            vol.Schema(
                {
                    vol.Required("entity_id"): str,
                    vol.Optional("species"): str,
                    vol.Optional("phases"): {
                        vol.Optional("sowing"): _PHASE_SCHEMA,
                        vol.Optional("germination"): _PHASE_SCHEMA,
                        vol.Optional("flowering"): _PHASE_SCHEMA,
                        vol.Optional("harvest"): _PHASE_SCHEMA,
                    },
                }
            )
        ],
        vol.Required("summary"): str,
    }
)


def _find_delegate_entity_id(hass: HomeAssistant) -> str | None:
    """Return an ai_task entity that supports GENERATE_DATA, excluding our own entities."""
    entity_registry = er.async_get(hass)
    our_entity_ids = {
        entry.entity_id
        for entry in entity_registry.entities.values()
        if entry.domain == Platform.AI_TASK and entry.platform == DOMAIN
    }
    component = hass.data.get(DATA_COMPONENT)
    if component is None:
        return None
    for entity in component.entities:
        if (
            entity.entity_id not in our_entity_ids
            and AITaskEntityFeature.GENERATE_DATA in entity.supported_features
        ):
            return entity.entity_id
    return None


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
        ]
    )
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

    async def _async_generate_data(
        self,
        task: GenDataTask,
        chat_log: ChatLog,  # noqa: ARG002
    ) -> GenDataTaskResult:
        """Enrich the task with crop context, delegate to an LLM, and add todos."""
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


class FillCropFieldsAITask(AITaskEntity):
    """
    AI task entity that fills missing fields on existing crops.

    When invoked, it:
    1. Identifies crops with missing species or incomplete phase dates.
    2. Delegates to another available AI task entity for LLM inference.
    3. Merges the returned suggestions back into the config entry, never
       overwriting values the user has already set.
    """

    _attr_supported_features = AITaskEntityFeature.GENERATE_DATA
    _attr_has_entity_name = True
    _attr_translation_key = "enrich_crop_data"

    def __init__(self, hass: HomeAssistant, entry: CropPlannerConfigEntry) -> None:
        """Initialise the entity."""
        coordinator: CropPlannerCoordinator = hass.data[DOMAIN][COORDINATOR]
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_enrich_crop_data"
        self._device_id = coordinator.device_id
        self.entity_id = async_generate_entity_id(
            f"{Platform.AI_TASK}.{{}}", "enrich crop data", current_ids={}
        )

    async def _async_generate_data(
        self,
        task: GenDataTask,
        chat_log: ChatLog,  # noqa: ARG002
    ) -> GenDataTaskResult:
        """Identify incomplete crops, ask the LLM to fill them, then persist."""
        crops: list[dict] = copy.deepcopy(list(self._entry.data.get(CONF_CROPS, [])))

        incomplete = [c for c in crops if self._crop_is_incomplete(c)]
        if not incomplete:
            LOGGER.debug("All crops are already complete; nothing to fill.")
            return GenDataTaskResult(conversation_id=None, data={"crops": [], "summary": "All crops are already complete."})

        delegate_entity_id = _find_delegate_entity_id(self._hass)
        if delegate_entity_id is None:
            msg = (
                "No AI task entity available to process the request. "
                "Set up an AI assistant integration (e.g. Google AI, OpenAI) first."
            )
            raise HomeAssistantError(msg)

        context = _build_context(self._hass, incomplete, [])
        instructions = f"{_FILL_FIELDS_INSTRUCTIONS}\n\nContext:\n{context}"

        LOGGER.debug("Delegating crop field filling to %s", delegate_entity_id)
        result = await async_generate_data(
            self._hass,
            task_name=task.name,
            entity_id=delegate_entity_id,
            instructions=instructions,
            structure=_FILL_FIELDS_SCHEMA,
        )
        LOGGER.debug("Received fill-fields response: %s", result)

        data: dict = result.data or {}
        suggestions: list[dict] = data.get("crops", [])
        summary: str = data.get("summary", "")
        LOGGER.debug("Fill-fields suggestions received (%d): %s", len(suggestions), suggestions)

        if suggestions:
            updated_count = self._merge_suggestions(crops, suggestions)
            LOGGER.debug("Filled fields for %d crop(s).", updated_count)
        else:
            LOGGER.debug("No suggestions returned by LLM.")

        if summary:
            async_create(
                self._hass,
                message=summary,
                title="🌱 Crop Planner – Crop data enriched",
                notification_id=f"{DOMAIN}_enrich_crop_data",
            )

        return result

    @staticmethod
    def _crop_is_incomplete(crop: dict[str, Any]) -> bool:
        """Return True if the crop is missing species or any phase dates."""
        if not crop.get("species"):
            return True
        phases: dict[str, dict] = crop.get("phases", {})
        for phase in CROP_PHASES:
            p = phases.get(phase, {})
            if not p.get("start") or not p.get("end"):
                return True
        return False

    def _merge_suggestions(
        self, crops: list[dict[str, Any]], suggestions: list[dict[str, Any]]
    ) -> int:
        """Merge AI suggestions into the crops list; never overwrite existing data."""
        entity_registry = er.async_get(self._hass)
        # Build a map from entity_id → crop UUID using the entity registry.
        suggestions_by_crop_id: dict[str, dict] = {}
        for suggestion in suggestions:
            entity_id = suggestion.get("entity_id")
            if not entity_id:
                LOGGER.debug("Suggestion missing entity_id: %s", suggestion)
                continue
            entry = entity_registry.async_get(entity_id)
            if entry and entry.unique_id:
                suggestions_by_crop_id[entry.unique_id] = suggestion
                LOGGER.debug("Mapped entity_id %s → crop id %s", entity_id, entry.unique_id)
            else:
                LOGGER.warning("Could not resolve entity_id %s in registry", entity_id)

        updated = 0
        for crop in crops:
            suggestion = suggestions_by_crop_id.get(crop["id"])
            if suggestion is None:
                continue
            changed = False
            # Fill species only if missing.
            if not crop.get("species") and suggestion.get("species"):
                crop["species"] = suggestion["species"]
                changed = True
            # Fill phase dates only where missing.
            suggested_phases: dict[str, dict] = suggestion.get("phases", {})
            # crop dicts from entry.data are plain dicts — safe to mutate.
            existing_phases: dict[str, dict] = crop.get("phases") or {}
            crop["phases"] = existing_phases
            for phase, phase_data in suggested_phases.items():
                if phase not in CROP_PHASES:
                    continue
                existing_phase = existing_phases.get(phase) or {}
                existing_phases[phase] = existing_phase
                for key in ("start", "end"):
                    if not existing_phase.get(key) and phase_data.get(key):
                        existing_phase[key] = phase_data[key]
                        changed = True
                        LOGGER.debug("Set %s.%s.%s = %s", crop.get("name"), phase, key, phase_data[key])
            if changed:
                updated += 1

        if updated:
            self._hass.config_entries.async_update_entry(
                self._entry,
                data={**self._entry.data, CONF_CROPS: crops},
            )
        return updated

    def update_registry(self) -> None:
        """Associate the entity with the integration device."""
        erreg = er.async_get(self._hass)
        erreg.async_update_entity(self.entity_id, device_id=self._device_id)

    async def async_added_to_hass(self) -> None:
        """Register in entity registry once added to hass."""
        self.update_registry()

