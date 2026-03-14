"""Tests for the Crop Planner options flow (adding crop entities via UI)."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crop.const import CONF_CROPS, DOMAIN

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
    """Submitting without a species skips OPB and creates the crop directly."""
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_crop"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"name": "Tomato", "quantity": 4, "sowing_date": "2026-03-01"},
    )
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
        "search_result": {
            _TOMATO_PID: {"display_pid": "Tomato", "pid": _TOMATO_PID},
            _WILD_TOMATO_PID: {"display_pid": "Wild Tomato", "pid": _WILD_TOMATO_PID},
        }
    }
    with patch(
        "custom_components.crop.config_flow.OpenPlantbookHelper"
    ) as mock_cls:
        mock_cls.return_value.openplantbook_search = AsyncMock(
            return_value=search_result
        )
        result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add_crop"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "name": "Tomato",
                "quantity": 2,
                "sowing_date": "2026-03-01",
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
        "search_result": {
            _TOMATO_PID: {"display_pid": "Tomato", "pid": _TOMATO_PID},
        }
    }
    opb_detail = {"image_url": "https://example.com/tomato.png"}

    with patch(
        "custom_components.crop.config_flow.OpenPlantbookHelper"
    ) as mock_cls:
        mock_cls.return_value.openplantbook_search = AsyncMock(
            return_value=search_result
        )
        mock_cls.return_value.openplantbook_get = AsyncMock(return_value=opb_detail)

        result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add_crop"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "name": "Tomato",
                "quantity": 1,
                "sowing_date": "2026-03-01",
                "species": "tomato",
            },
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"species": _TOMATO_PID}
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
        "search_result": {
            _TOMATO_PID: {"display_pid": "Tomato", "pid": _TOMATO_PID},
        }
    }
    with patch(
        "custom_components.crop.config_flow.OpenPlantbookHelper"
    ) as mock_cls:
        mock_cls.return_value.openplantbook_search = AsyncMock(
            return_value=search_result
        )
        result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add_crop"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "name": "Basil",
                "quantity": 1,
                "sowing_date": "2026-03-01",
                "species": "basil",
            },
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"species": "__none__"}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    crops = loaded_entry.data.get(CONF_CROPS, [])
    assert crops[0]["species"] is None
    assert crops[0]["image_url"] is None


async def test_options_flow_search_fails_still_shows_select(hass, loaded_entry):
    """If OPB search raises, the select step still appears with only 'None'."""
    with patch(
        "custom_components.crop.config_flow.OpenPlantbookHelper"
    ) as mock_cls:
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
                "sowing_date": "2026-03-01",
                "species": "pepper",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_species"
    options = result["data_schema"].schema["species"].config["options"]
    assert len(options) == 1
    assert options[0]["value"] == "__none__"
