"""Tests for the create_crop service."""

from unittest.mock import patch

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
    await hass.services.async_call(
        DOMAIN,
        "create_crop",
        {"name": "Basil", "quantity": 2, "sowing_date": "2024-05-01"},
        blocking=True,
    )
    await hass.async_block_till_done()

    crops = setup_integration.data.get("crops", [])
    assert any(c["name"] == "Basil" for c in crops)


async def test_create_crop_without_species_skips_openplantbook(hass, setup_integration):
    """OpenPlantbook is not queried when no species is provided."""
    with patch(
        "custom_components.crop.service.OpenPlantbookHelper.openplantbook_get"
    ) as mock_opb:
        await hass.services.async_call(
            DOMAIN,
            "create_crop",
            {"name": "Oregano", "quantity": 1},
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_opb.assert_not_called()


async def test_create_crop_with_species_sets_image_url(hass, setup_integration):
    """image_url is stored on the crop when OpenPlantbook returns data."""
    opb_response = {"image_url": "https://example.com/tomato.jpg"}
    with patch(
        "custom_components.crop.service.OpenPlantbookHelper.openplantbook_get",
        return_value=opb_response,
    ):
        await hass.services.async_call(
            DOMAIN,
            "create_crop",
            {"name": "Cherry Tomato", "quantity": 5, "species": "Tomato"},
            blocking=True,
        )
        await hass.async_block_till_done()

    crops = setup_integration.data.get("crops", [])
    crop = next(c for c in crops if c["name"] == "Cherry Tomato")
    assert crop["image_url"] == "https://example.com/tomato.jpg"


async def test_create_crop_with_unavailable_openplantbook(hass, setup_integration):
    """Crop is still created when OpenPlantbook returns None (unavailable/not found)."""
    with patch(
        "custom_components.crop.service.OpenPlantbookHelper.openplantbook_get",
        return_value=None,
    ):
        await hass.services.async_call(
            DOMAIN,
            "create_crop",
            {"name": "Mint", "quantity": 3, "species": "Mentha"},
            blocking=True,
        )
        await hass.async_block_till_done()

    crops = setup_integration.data.get("crops", [])
    crop = next(c for c in crops if c["name"] == "Mint")
    assert crop.get("image_url") is None
