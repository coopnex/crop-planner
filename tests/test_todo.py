"""Tests for the CropTodoList entity."""

from unittest.mock import patch

import pytest
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crop.const import CONF_CROPS, CONF_TODOS, DOMAIN

_TODO_ENTITY = "todo.crop_chores"


@pytest.fixture
async def loaded_entry(hass):
    """Config entry with no initial todos."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Crop Planner",
        data={CONF_CROPS: [], CONF_TODOS: []},
        unique_id="crop",
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    return entry


@pytest.fixture
async def entry_with_todo(hass):
    """Config entry pre-loaded with one todo that has extra attributes."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Crop Planner",
        data={
            CONF_CROPS: [],
            CONF_TODOS: [
                {
                    "uid": "uid-1",
                    "summary": "💧 Water tomatoes",
                    "status": "needs_action",
                    "due": "2026-03-20",
                    "description": "Check moisture",
                    "crop_entity_id": "crop.tomato",
                    "category": "watering",
                }
            ],
        },
        unique_id="crop",
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    return entry


async def test_todo_entity_created(hass, loaded_entry):
    """The todo list entity is registered after setup."""
    assert hass.states.get(_TODO_ENTITY) is not None


async def test_add_todo_item_persists(hass, loaded_entry):
    """Adding a todo item via service persists it to the config entry."""
    await hass.services.async_call(
        "todo",
        "add_item",
        {"entity_id": _TODO_ENTITY, "item": "Pull weeds"},
        blocking=True,
    )
    await hass.async_block_till_done()

    todos = loaded_entry.data.get(CONF_TODOS, [])
    assert any(t["summary"] == "Pull weeds" for t in todos)


async def test_delete_todo_item_removes_from_entry(hass, entry_with_todo):
    """Deleting a todo item removes it from the config entry."""
    await hass.services.async_call(
        "todo",
        "remove_item",
        {"entity_id": _TODO_ENTITY, "item": ["uid-1"]},
        blocking=True,
    )
    await hass.async_block_till_done()

    todos = entry_with_todo.data.get(CONF_TODOS, [])
    assert not any(t["uid"] == "uid-1" for t in todos)


async def test_extra_attributes_preserved_on_update(hass, entry_with_todo):
    """crop_entity_id and category survive a todo item update."""
    await hass.services.async_call(
        "todo",
        "update_item",
        {
            "entity_id": _TODO_ENTITY,
            "item": "uid-1",
            "due_date": "2026-03-25",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    todos = entry_with_todo.data.get(CONF_TODOS, [])
    item = next(t for t in todos if t["uid"] == "uid-1")
    assert item.get("crop_entity_id") == "crop.tomato"
    assert item.get("category") == "watering"


async def test_completion_fires_logbook_entry(hass, entry_with_todo):
    """Marking a todo with crop_entity_id as completed fires a logbook entry."""
    with patch("custom_components.crop.todo.async_log_entry") as mock_log:
        await hass.services.async_call(
            "todo",
            "update_item",
            {
                "entity_id": _TODO_ENTITY,
                "item": "uid-1",
                "status": "completed",
            },
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_log.assert_called_once()
    call_kwargs = mock_log.call_args
    assert call_kwargs.kwargs.get("entity_id") == "crop.tomato"


async def test_completion_without_crop_entity_id_no_logbook(hass, loaded_entry):
    """Completing a todo without crop_entity_id does not fire a logbook entry."""
    await hass.services.async_call(
        "todo",
        "add_item",
        {"entity_id": _TODO_ENTITY, "item": "General task"},
        blocking=True,
    )
    await hass.async_block_till_done()

    todos = loaded_entry.data.get(CONF_TODOS, [])
    uid = next(t["uid"] for t in todos if t["summary"] == "General task")

    with patch("custom_components.crop.todo.async_log_entry") as mock_log:
        await hass.services.async_call(
            "todo",
            "update_item",
            {"entity_id": _TODO_ENTITY, "item": uid, "status": "completed"},
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_log.assert_not_called()
