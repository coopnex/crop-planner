"""Tests for integration setup and teardown."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crop.const import DOMAIN


async def test_setup_with_no_crops(hass):
    """Integration loads successfully when the config entry has no crops."""
    entry = MockConfigEntry(
        domain=DOMAIN, title="Crop Planner", data={}, unique_id="crop"
    )
    entry.add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED


async def test_setup_creates_crop_entities(hass):
    """A crop entity is created for each crop stored in the config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Crop Planner",
        data={
            "crops": [
                {
                    "id": "test-id-1",
                    "name": "Tomato",
                    "quantity": 3,
                }
            ]
        },
        unique_id="crop",
    )
    entry.add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    state = hass.states.get("crop.tomato")
    assert state is not None
    assert state.attributes["quantity"] == 3
    assert state.attributes["species"] is None


async def test_setup_crop_entity_with_species(hass):
    """Species and image_url are reflected in the entity state attributes."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Crop Planner",
        data={
            "crops": [
                {
                    "id": "test-id-2",
                    "name": "Basil",
                    "quantity": 1,
                    "species": "ocimum basilicum",
                    "image_url": "https://example.com/basil.jpg",
                }
            ]
        },
        unique_id="crop",
    )
    entry.add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    state = hass.states.get("crop.basil")
    assert state is not None
    assert state.attributes["species"] == "ocimum basilicum"


async def test_unload_entry(hass):
    """Config entry can be unloaded cleanly."""
    entry = MockConfigEntry(
        domain=DOMAIN, title="Crop Planner", data={}, unique_id="crop"
    )
    entry.add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
