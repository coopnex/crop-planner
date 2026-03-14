"""Todo platform for the Crop Planner integration — crop chore tracking."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from homeassistant.components.logbook import async_log_entry
from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.const import Platform
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import async_generate_entity_id

from .const import CHORE_CATEGORY_ICONS, CONF_TODOS, COORDINATOR, DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import CropPlannerConfigEntry, CropPlannerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CropPlannerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the crop todo list."""
    async_add_entities([CropTodoList(hass, entry)])
    return True


class CropTodoList(TodoListEntity):
    """A todo list for tracking crop chores."""

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.SET_DUE_DATE_ON_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )
    _attr_has_entity_name = True
    _attr_translation_key = "crop_chores"

    def __init__(self, hass: HomeAssistant, entry: CropPlannerConfigEntry) -> None:
        """Initialise the todo list entity."""
        coordinator: CropPlannerCoordinator = hass.data[DOMAIN][COORDINATOR]
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_todos"
        self._device_id = coordinator.device_id
        self.entity_id = async_generate_entity_id(
            f"{Platform.TODO}.{{}}", "crop chores", current_ids={}
        )
        self._load_items()

    def _load_items(self) -> None:
        """Load todo items from the config entry."""
        self._attr_todo_items = [
            TodoItem(
                uid=t["uid"],
                summary=t["summary"],
                status=TodoItemStatus(t.get("status", TodoItemStatus.NEEDS_ACTION)),
                due=t.get("due"),
                description=t.get("description"),
            )
            for t in self._entry.data.get(CONF_TODOS, [])
        ]

    def _persist(self) -> None:
        """Write current todo items back to the config entry."""
        _KNOWN_KEYS = {"uid", "summary", "status", "due", "description"}  # noqa: N806
        stored_by_uid = {t["uid"]: t for t in self._entry.data.get(CONF_TODOS, [])}
        self._hass.config_entries.async_update_entry(
            self._entry,
            data={
                **self._entry.data,
                CONF_TODOS: [
                    {
                        **{
                            k: v
                            for k, v in stored_by_uid.get(item.uid, {}).items()
                            if k not in _KNOWN_KEYS
                        },
                        "uid": item.uid,
                        "summary": item.summary,
                        "status": item.status,
                        "due": item.due,
                        "description": item.description,
                    }
                    for item in (self._attr_todo_items or [])
                ],
            },
        )

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add a new chore."""
        item.uid = str(uuid.uuid4())
        self._attr_todo_items = [*list(self._attr_todo_items or []), item]
        self._persist()
        self.async_write_ha_state()
        LOGGER.debug("Created todo item: %s", item.summary)

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an existing chore (rename, complete, set due date…)."""
        items = list(self._attr_todo_items or [])
        for i, existing in enumerate(items):
            if existing.uid == item.uid:
                if (
                    item.status == TodoItemStatus.COMPLETED
                    and existing.status != TodoItemStatus.COMPLETED
                ):
                    self._log_completion(item)
                items[i] = item
                break
        self._attr_todo_items = items
        self._persist()
        self.async_write_ha_state()

    def _log_completion(self, item: TodoItem) -> None:
        """Fire a logbook entry against the crop entity when a chore is completed."""
        stored = {t["uid"]: t for t in self._entry.data.get(CONF_TODOS, [])}
        stored_item = stored.get(item.uid, {})
        crop_entity_id = stored_item.get("crop_entity_id")
        if not crop_entity_id:
            return
        async_log_entry(
            self._hass,
            name=crop_entity_id,
            message=f"{item.summary}",
            domain=DOMAIN,
            entity_id=crop_entity_id,
        )

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Remove one or more chores."""
        uid_set = set(uids)
        self._attr_todo_items = [
            item for item in (self._attr_todo_items or []) if item.uid not in uid_set
        ]
        self._persist()
        self.async_write_ha_state()

    def update_registry(self) -> None:
        """Associate the entity with the integration device."""
        erreg = er.async_get(self._hass)
        erreg.async_update_entity(self.entity_id, device_id=self._device_id)

    async def async_added_to_hass(self) -> None:
        """Register in the entity registry once added to hass."""
        self.update_registry()
