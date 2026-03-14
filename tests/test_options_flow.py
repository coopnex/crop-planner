"""Tests for the Crop Planner options flow (adding crop entities via UI)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crop.const import CONF_CROPS, CONF_TODOS, DOMAIN

_TOMATO_PID = "solanum lycopersicum"
_WILD_TOMATO_PID = "solanum pimpinellifolium"


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
    assert "add_crop" in result["menu_options"]
    assert "finish" in result["menu_options"]


async def test_options_flow_finish_without_adding(hass, loaded_entry):
    """Selecting 'finish' closes the flow without changes."""
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_options_flow_add_crop_shows_form(hass, loaded_entry):
    """Selecting 'add_crop' shows the crop form."""
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_crop"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_crop"


async def test_options_flow_add_crop_no_species_creates_entity(hass, loaded_entry):
    """Submitting without OPB credentials shows select_species with only None, then phases."""  # noqa: E501
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_crop"}
    )
    # Add crop form — no species hint, no OPB credentials configured
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"name": "Tomato", "quantity": 4},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_species"

    # Select "— None —"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"species": "__none__"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "phases"

    # Submit phases (empty — all optional)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    crops = loaded_entry.data.get(CONF_CROPS, [])
    assert len(crops) == 1
    assert crops[0]["name"] == "Tomato"
    assert crops[0]["quantity"] == 4
    assert crops[0]["species"] is None
    assert hass.states.get("crop.tomato") is not None


async def test_options_flow_species_hint_shows_select_form(hass, loaded_entry):
    """Entering a species hint triggers OPB search and shows the select step."""
    search_result = {
        "results": [
            {"pid": _TOMATO_PID, "display_pid": "Tomato"},
            {"pid": _WILD_TOMATO_PID, "display_pid": "Wild Tomato"},
        ]
    }
    mock_helper = AsyncMock()
    mock_helper.openplantbook_search = AsyncMock(return_value=search_result)
    with patch(
        "custom_components.crop.config_flow.CropPlannerOptionsFlowHandler._opb_helper",
        return_value=mock_helper,
    ):
        result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add_crop"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "name": "Tomato",
                "quantity": 2,
                "species": "tomato",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_species"
    options = result["data_schema"].schema["species"].config["options"]
    labels = [o["label"] for o in options]
    assert "Tomato" in labels
    assert "Wild Tomato" in labels


async def test_options_flow_select_species_creates_entity_with_image(
    hass, loaded_entry
):
    """Selecting a species fetches OPB details and stores image_url."""
    search_result = {
        "results": [
            {"pid": _TOMATO_PID, "display_pid": "Tomato"},
        ]
    }
    opb_detail = {"image_url": "https://example.com/tomato.png"}

    mock_helper = AsyncMock()
    mock_helper.openplantbook_search = AsyncMock(return_value=search_result)
    mock_helper.openplantbook_get = AsyncMock(return_value=opb_detail)
    with patch(
        "custom_components.crop.config_flow.CropPlannerOptionsFlowHandler._opb_helper",
        return_value=mock_helper,
    ):
        result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add_crop"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "name": "Tomato",
                "quantity": 1,
                "species": "tomato",
            },
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"species": _TOMATO_PID}
        )
        assert result["step_id"] == "phases"
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    crops = loaded_entry.data.get(CONF_CROPS, [])
    assert crops[0]["species"] == _TOMATO_PID
    assert crops[0]["image_url"] == "https://example.com/tomato.png"
    assert hass.states.get("crop.tomato") is not None


async def test_options_flow_select_none_species(hass, loaded_entry):
    """Selecting '— None —' creates the crop without a species."""
    search_result = {
        "results": [
            {"pid": _TOMATO_PID, "display_pid": "Tomato"},
        ]
    }
    mock_helper = AsyncMock()
    mock_helper.openplantbook_search = AsyncMock(return_value=search_result)
    with patch(
        "custom_components.crop.config_flow.CropPlannerOptionsFlowHandler._opb_helper",
        return_value=mock_helper,
    ):
        result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add_crop"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "name": "Basil",
                "quantity": 1,
                "species": "basil",
            },
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"species": "__none__"}
        )
        assert result["step_id"] == "phases"
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    crops = loaded_entry.data.get(CONF_CROPS, [])
    assert crops[0]["species"] is None
    assert crops[0]["image_url"] is None


async def test_options_flow_search_fails_still_shows_select(hass, loaded_entry):
    """If OPB search raises, the select step still appears with only 'None'."""
    with patch("custom_components.crop.config_flow.OpenPlantbookHelper") as mock_cls:
        mock_cls.return_value.openplantbook_search = AsyncMock(
            side_effect=Exception("OPB down")
        )
        result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add_crop"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "name": "Pepper",
                "quantity": 1,
                "species": "pepper",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_species"
    options = result["data_schema"].schema["species"].config["options"]
    assert len(options) == 1
    assert options[0]["value"] == "__none__"


# ---------------------------------------------------------------------------
# Crop name capitalisation
# ---------------------------------------------------------------------------


async def test_add_crop_name_is_capitalised(hass, loaded_entry):
    """Crop names are stored with the first letter capitalised."""
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_crop"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"name": "cherry tomato", "quantity": 1}
    )
    # select_species → pick none
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"species": "__none__"}
    )
    # phases → submit empty
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    crop = loaded_entry.data[CONF_CROPS][0]
    assert crop["name"] == "Cherry tomato"


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
