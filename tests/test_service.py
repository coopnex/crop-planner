"""Tests for the create_crop service."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crop.const import DOMAIN


@pytest.fixture
async def setup_integration(hass):
    """Load the Crop Planner integration and return the config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN, title="Crop Planner", data={}, unique_id="crop"
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    return entry


async def test_create_crop_persists_in_config_entry(hass, setup_integration):
    """create_crop service stores the new crop in the config entry data."""
    with patch(
        "custom_components.crop.service._enrich_crop", new_callable=AsyncMock
    ):
        await hass.services.async_call(
            DOMAIN,
            "create_crop",
            {"name": "Basil", "quantity": 2},
            blocking=True,
        )
        await hass.async_block_till_done()

    crops = setup_integration.data.get("crops", [])
    assert any(c["name"] == "Basil" for c in crops)


async def test_create_crop_triggers_enrichment(hass, setup_integration):
    """create_crop schedules the AI enrichment task after adding a crop."""
    with patch(
        "custom_components.crop.service._enrich_crop", new_callable=AsyncMock
    ) as mock_enrich:
        await hass.services.async_call(
            DOMAIN,
            "create_crop",
            {"name": "Oregano", "quantity": 1},
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_enrich.assert_called_once()


async def test_create_crop_stores_provided_species(hass, setup_integration):
    """Species provided at creation time is stored on the crop."""
    with patch(
        "custom_components.crop.service._enrich_crop", new_callable=AsyncMock
    ):
        await hass.services.async_call(
            DOMAIN,
            "create_crop",
            {"name": "Cherry Tomato", "quantity": 5, "species": "Solanum lycopersicum"},
            blocking=True,
        )
        await hass.async_block_till_done()

    crops = setup_integration.data.get("crops", [])
    crop = next(c for c in crops if c["name"].lower() == "cherry tomato")
    assert crop["species"] == "Solanum lycopersicum"


async def test_create_crop_without_species_has_none(hass, setup_integration):
    """Crop is created with species=None when none is provided."""
    with patch(
        "custom_components.crop.service._enrich_crop", new_callable=AsyncMock
    ):
        await hass.services.async_call(
            DOMAIN,
            "create_crop",
            {"name": "Mint", "quantity": 3},
            blocking=True,
        )
        await hass.async_block_till_done()

    crops = setup_integration.data.get("crops", [])
    crop = next(c for c in crops if c["name"] == "Mint")
    assert crop.get("species") is None
    assert crop.get("image_url") is None
