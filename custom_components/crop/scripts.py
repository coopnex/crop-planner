"""Ensure integration-owned HA scripts are present in scripts.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from .const import LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_ADD_CROP_SCRIPT_ID = "add_crop"

_ADD_CROP_SCRIPT: dict = {
    "alias": "Add Crop",
    "icon": "mdi:sprout-outline",
    "fields": {
        "name": {
            "name": "Name",
            "description": "Name of the crop",
            "required": True,
            "example": "Tomato",
            "selector": {"text": {}},
        },
        "quantity": {
            "name": "Quantity",
            "description": "Number of plants",
            "required": True,
            "default": 1,
            "example": 3,
            "selector": {"number": {"min": 1, "max": 50, "step": 1, "mode": "box"}},
        },
        "species": {
            "name": "Species",
            "description": "Species hint for OpenPlantbook lookup (optional)",
            "required": False,
            "example": "Solanum lycopersicum",
            "selector": {"text": {}},
        },
    },
    "sequence": [
        {
            "action": "crop.create_crop",
            "data": {
                "name": "{{ name }}",
                "quantity": "{{ quantity | int }}",
                "species": "{{ species | default('') }}",
            },
        }
    ],
}


async def async_ensure_scripts(hass: HomeAssistant) -> None:
    """Write integration scripts to scripts.yaml if not already present."""
    scripts_path = Path(hass.config.config_dir) / "scripts.yaml"

    def _load() -> dict:
        if not scripts_path.exists():
            return {}
        content = scripts_path.read_text(encoding="utf-8")
        return yaml.safe_load(content) or {}

    def _save(scripts: dict) -> None:
        scripts_path.write_text(
            yaml.dump(scripts, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    scripts = await hass.async_add_executor_job(_load)

    if _ADD_CROP_SCRIPT_ID in scripts:
        return

    LOGGER.info("Installing script '%s' into scripts.yaml", _ADD_CROP_SCRIPT_ID)
    scripts[_ADD_CROP_SCRIPT_ID] = _ADD_CROP_SCRIPT
    await hass.async_add_executor_job(_save, scripts)
    await hass.services.async_call("script", "reload")
