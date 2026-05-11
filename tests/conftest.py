"""Common fixtures for Crop Planner tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""


@pytest.fixture(autouse=True)
def mock_exposed_entities(hass):
    """Provide homeassistant.exposed_entities so ai_task's conversation dep doesn't fail."""
    from homeassistant.components.homeassistant.exposed_entities import (
        DATA_EXPOSED_ENTITIES,
    )

    hass.data.setdefault(DATA_EXPOSED_ENTITIES, MagicMock())


@pytest.fixture(autouse=True)
def mock_ensure_scripts():
    """Prevent async_ensure_scripts from writing to disk or calling script.reload."""
    with patch(
        "custom_components.crop.async_ensure_scripts",
        new=AsyncMock(),
    ):
        yield


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Prevent real integration setup during config flow tests."""
    with patch(
        "custom_components.crop.async_setup_entry",
        return_value=True,
    ) as mock:
        yield mock
