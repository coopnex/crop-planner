"""AI task entity for filling missing fields on existing crops."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

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
from .const import CONF_CROPS, COORDINATOR, CROP_PHASES, DOMAIN, LOGGER, AIState

if TYPE_CHECKING:
    from homeassistant.components.conversation import ChatLog
    from homeassistant.core import HomeAssistant

    from .coordinator import CropPlannerConfigEntry, CropPlannerCoordinator

_FILL_FIELDS_INSTRUCTIONS = (
    "You are an expert horticulturist. "
    "For each crop listed in the context that has incomplete "
    "phase dates, fill in the blanks using your knowledge of the plant and the "
    "gardener's location and current date. "
    "Rules:\n"
    "- For each phase (sowing, germination, flowering, harvest) that lacks a start "
    "  or end date, estimate sensible dates based on the species, climate of the "
    "  location, and any existing dates already recorded for that crop.\n"
    "- Only fill in fields that are genuinely missing; "
    "never overwrite existing values.\n"
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


class FillCropFieldsAITask(AITaskEntity):
    """
    AI task entity that fills missing fields on existing crops.

    When invoked, it:
    1. Identifies crops with missing species or incomplete phase dates.
    2. Delegates to another available AI task entity for LLM inference.
    3. Merges the returned suggestions back into the config entry, never
       overwriting values the user has already set.
    """

    _attr_should_poll = False
    _attr_supported_features = AITaskEntityFeature.GENERATE_DATA
    _attr_has_entity_name = True
    _attr_translation_key = "enrich_crop_data"

    def __init__(self, hass: HomeAssistant, entry: CropPlannerConfigEntry) -> None:
        """Initialise the entity."""
        coordinator: CropPlannerCoordinator = hass.data[DOMAIN][COORDINATOR]
        self._hass = hass
        self._entry = entry
        self._coordinator = coordinator
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
        self._coordinator.set_ai_state(AIState.FILLING_FIELDS)
        try:
            return await self._async_generate_data_inner(task)
        finally:
            self._coordinator.set_ai_state(AIState.IDLE)

    async def _async_generate_data_inner(self, task: GenDataTask) -> GenDataTaskResult:
        """Inner implementation of generate data."""
        crops: list[dict] = copy.deepcopy(list(self._entry.data.get(CONF_CROPS, [])))

        incomplete = [c for c in crops if self._crop_is_incomplete(c)]
        if not incomplete:
            LOGGER.debug("All crops are already complete; nothing to fill.")
            return GenDataTaskResult(
                conversation_id=None,
                data={"crops": [], "summary": "All crops are already complete."},
            )

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
        summary = data.get("summary", "")
        LOGGER.debug(
            "Fill-fields suggestions received (%d): %s", len(suggestions), suggestions
        )

        if suggestions:
            updated_count = self._merge_suggestions_in_memory(crops, suggestions)
            LOGGER.debug("Filled fields for %d crop(s).", updated_count)
        else:
            LOGGER.debug("No suggestions returned by LLM.")

        if summary:
            async_create(
                self._hass,
                message=summary,
                title="🌱 Crop Planner - Crop data enriched",
                notification_id=f"{DOMAIN}_enrich_crop_data",
            )

        return result

    @staticmethod
    def _crop_is_incomplete(crop: dict[str, Any]) -> bool:
        """Return True if the crop is missing phase dates."""
        phases: dict[str, dict] = crop.get("phases", {})
        for phase in CROP_PHASES:
            p = phases.get(phase, {})
            if not p.get("start") or not p.get("end"):
                return True
        return False

    @staticmethod
    def _merge_phases(crop: dict[str, Any], suggested_phases: dict[str, dict]) -> bool:
        """Fill missing phase dates from suggestions. Returns True if any changed."""
        existing_phases: dict[str, dict] = crop.get("phases") or {}
        crop["phases"] = existing_phases
        changed = False
        for phase, phase_data in suggested_phases.items():
            if phase not in CROP_PHASES:
                continue
            existing_phase = existing_phases.get(phase) or {}
            existing_phases[phase] = existing_phase
            for key in ("start", "end"):
                if not existing_phase.get(key) and phase_data.get(key):
                    existing_phase[key] = phase_data[key]
                    changed = True
                    LOGGER.debug(
                        "Set %s.%s.%s = %s",
                        crop.get("name"),
                        phase,
                        key,
                        phase_data[key],
                    )
        return changed

    def _merge_suggestions_in_memory(
        self, crops: list[dict[str, Any]], suggestions: list[dict[str, Any]]
    ) -> int:
        """Merge AI suggestions into crops in-memory; never overwrite existing data."""
        entity_registry = er.async_get(self._hass)
        suggestions_by_crop_id: dict[str, dict] = {}
        for suggestion in suggestions:
            entity_id = suggestion.get("entity_id")
            if not entity_id:
                LOGGER.debug("Suggestion missing entity_id: %s", suggestion)
                continue
            entry = entity_registry.async_get(entity_id)
            if entry and entry.unique_id:
                suggestions_by_crop_id[entry.unique_id] = suggestion
                LOGGER.debug("Mapped %s -> crop id %s", entity_id, entry.unique_id)
            else:
                LOGGER.warning("Could not resolve entity_id %s in registry", entity_id)

        updated = 0
        for crop in crops:
            suggestion = suggestions_by_crop_id.get(crop["id"])
            if suggestion is None:
                continue
            changed = False
            if suggestion.get("phases"):
                changed = self._merge_phases(crop, suggestion["phases"]) or changed
            if changed:
                updated += 1

        return updated

    def _save_crops(self, crops: list[dict[str, Any]]) -> None:
        """Persist the crops list to the config entry."""
        self._hass.config_entries.async_update_entry(
            self._entry,
            data={**self._entry.data, CONF_CROPS: crops},
        )

    def update_registry(self) -> None:
        """Associate the entity with the integration device."""
        erreg = er.async_get(self._hass)
        erreg.async_update_entity(self.entity_id, device_id=self._device_id)

    async def async_added_to_hass(self) -> None:
        """Register in entity registry once added to hass."""
        self.update_registry()
