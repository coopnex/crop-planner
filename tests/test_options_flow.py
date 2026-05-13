"""Tests for the Crop Planner options flow."""

import uuid

import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crop.const import CONF_CROPS, CONF_TODOS, DOMAIN


@pytest.fixture
async def loaded_entry(hass):
    """Set up a loaded config entry with no crops."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Crop Planner",
        data={CONF_CROPS: []},
        unique_id="crop",
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    return entry


async def test_options_flow_shows_menu(hass, loaded_entry):
    """Options flow init step shows a menu."""
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"
    assert "remove_crops" in result["menu_options"]
    assert "clear_todos" in result["menu_options"]


# ---------------------------------------------------------------------------
# Remove crops (multi-select)
# ---------------------------------------------------------------------------


@pytest.fixture
async def entry_with_two_crops(hass):
    """Config entry pre-loaded with two crops."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Crop Planner",
        data={
            CONF_CROPS: [
                {"id": "id-1", "name": "Tomato", "quantity": 1, "phases": {}},
                {"id": "id-2", "name": "Basil", "quantity": 2, "phases": {}},
            ]
        },
        unique_id="crop",
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    return entry


async def test_remove_crops_shows_multi_select(hass, entry_with_two_crops):
    """remove_crops step shows a multi-select with all existing crops."""
    result = await hass.config_entries.options.async_init(entry_with_two_crops.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_crops"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "remove_crops"
    options = result["data_schema"].schema["crop_ids"].config["options"]
    labels = [o["label"] for o in options]
    assert "Tomato" in labels
    assert "Basil" in labels


async def test_remove_single_crop(hass, entry_with_two_crops):
    """Selecting one crop removes only that crop."""
    result = await hass.config_entries.options.async_init(entry_with_two_crops.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_crops"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"crop_ids": ["id-1"]}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    crops = entry_with_two_crops.data[CONF_CROPS]
    assert len(crops) == 1
    assert crops[0]["id"] == "id-2"


async def test_remove_multiple_crops(hass, entry_with_two_crops):
    """Selecting both crops removes all of them."""
    result = await hass.config_entries.options.async_init(entry_with_two_crops.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_crops"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"crop_ids": ["id-1", "id-2"]}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry_with_two_crops.data[CONF_CROPS] == []


async def test_remove_all_crops_via_checkbox(hass, entry_with_two_crops):
    """Checking 'remove_all' removes all crops regardless of selection."""
    result = await hass.config_entries.options.async_init(entry_with_two_crops.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_crops"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"remove_all": True, "crop_ids": []}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry_with_two_crops.data[CONF_CROPS] == []


# ---------------------------------------------------------------------------
# Clear todos
# ---------------------------------------------------------------------------


@pytest.fixture
async def entry_with_todos(hass):
    """Config entry pre-loaded with one todo item."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Crop Planner",
        data={
            CONF_CROPS: [],
            CONF_TODOS: [
                {
                    "uid": str(uuid.uuid4()),
                    "summary": "Water plants",
                    "status": "needs_action",
                    "due": None,
                    "description": None,
                }
            ],
        },
        unique_id="crop",
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    return entry


async def test_clear_todos_shows_confirmation_form(hass, entry_with_todos):
    """clear_todos step shows a confirmation form."""
    result = await hass.config_entries.options.async_init(entry_with_todos.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "clear_todos"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "clear_todos"


async def test_clear_todos_removes_all_items(hass, entry_with_todos):
    """Confirming clear_todos empties the todos list."""
    result = await hass.config_entries.options.async_init(entry_with_todos.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "clear_todos"}
    )
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry_with_todos.data.get("todos", []) == []
