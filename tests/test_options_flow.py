"""Tests for the Crop Planner options flow (adding crop entities via UI)."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crop.const import CONF_CROPS, DOMAIN


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


async def test_options_flow_add_crop_creates_entity(hass, loaded_entry):
    """Submitting the add_crop form appends the crop and creates the entity."""
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_crop"}
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "name": "Tomato",
            "quantity": 4,
            "sowing_date": "2026-03-01",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY

    crops = loaded_entry.data.get(CONF_CROPS, [])
    assert len(crops) == 1
    assert crops[0]["name"] == "Tomato"
    assert crops[0]["quantity"] == 4
    assert crops[0]["sowing_date"] == "2026-03-01"
    assert crops[0]["species"] is None

    state = hass.states.get("crop.tomato")
    assert state is not None
    assert state.attributes["quantity"] == 4


async def test_options_flow_add_crop_with_species_no_opb(hass, loaded_entry):
    """A crop with species but no OpenPlantbook result still creates the entity."""
    with patch(
        "custom_components.crop.config_flow.OpenPlantbookHelper",
    ) as mock_opb_cls:
        mock_opb_cls.return_value.openplantbook_get = AsyncMock(return_value=None)

        result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add_crop"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "name": "Basil",
                "quantity": 2,
                "sowing_date": "2026-04-01",
                "species": "ocimum basilicum",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    crops = loaded_entry.data.get(CONF_CROPS, [])
    assert len(crops) == 1
    assert crops[0]["species"] == "ocimum basilicum"
    assert crops[0]["image_url"] is None

    state = hass.states.get("crop.basil")
    assert state is not None


async def test_options_flow_add_crop_with_opb_image(hass, loaded_entry):
    """When OpenPlantbook returns data, image_url is stored on the crop."""
    with patch(
        "custom_components.crop.config_flow.OpenPlantbookHelper",
    ) as mock_opb_cls:
        mock_opb_cls.return_value.openplantbook_get = AsyncMock(
            return_value={"image_url": "https://example.com/basil.png"}
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
                "sowing_date": "2026-04-01",
                "species": "ocimum basilicum",
            },
        )
        await hass.async_block_till_done()

    crops = loaded_entry.data.get(CONF_CROPS, [])
    assert crops[0]["image_url"] == "https://example.com/basil.png"
