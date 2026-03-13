"""Tests for the Crop Planner config flow."""

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.crop.const import CROP_PLANNER, DOMAIN


async def test_user_step_shows_form(hass, mock_setup_entry):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_user_step_creates_entry(hass, mock_setup_entry):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == CROP_PLANNER
    assert mock_setup_entry.call_count == 1


async def test_second_flow_aborts_as_duplicate(hass, mock_setup_entry):
    """A second config flow is aborted because only one instance is allowed."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
