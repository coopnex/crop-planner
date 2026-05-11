"""
Crop Planner integration: entities and data structures for crops.

This module provides the CropData dataclass and the Crop Entity used by the
Crop Planner Home Assistant integration to represent planted crops, their
quantities, and device/entity registration behavior.
"""

from datetime import UTC, datetime
from typing import ClassVar

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import STATE_OK
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.entity import (
    Entity,
    async_generate_entity_id,
)

from custom_components.crop.data import (
    CropData,
)

from .const import (
    CROP_PHASES,
    CROP_PLATFORM,
    ICON,
    ChoreCategory,
)


class Crop(Entity):
    """Class to represent a crop."""

    _attr_should_poll = True
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options: ClassVar[list[str]] = [
        STATE_OK,
        *CROP_PHASES,
        *[c.value for c in ChoreCategory],
    ]
    _attr_translation_key = "crop"

    def __init__(self, hass: HomeAssistant, config: CropData) -> None:
        """Initialize a crop with a name, planting date, and harvest date."""
        self._hass = hass
        self._attr_name = config.name
        self._quantity = config.quantity
        self._species = config.species
        self._phases = config.phases
        if config.image_url is not None:
            self._attr_entity_picture = config.image_url
        else:
            self._attr_entity_picture = None
        self._config_entries = []
        self._unique_id = config.id
        self._attr_unique_id = self._unique_id
        self.entity_id = async_generate_entity_id(
            f"{CROP_PLATFORM}.{{}}", config.name, current_ids={}
        )
        self._attr_icon = ICON
        self._attr_state = STATE_OK  # computed properly on first update()

    @property
    def name(self) -> str:
        """Return the name of the crop."""
        return self._attr_name

    @property
    def quantity(self) -> int:
        """Return the quantity of the crop."""
        return self._quantity

    @property
    def extra_state_attributes(self) -> dict:
        """Return the device specific state attributes."""
        return {
            "name": self._attr_name,
            "quantity": self._quantity,
            "species": self._species,
            "phases": {
                phase: phase_data.to_dict()
                for phase, phase_data in self._phases.items()
            },
        }

    def update(self) -> None:
        """Run on every update of the entities."""
        self._attr_state = self._compute_state()

    def _compute_state(self) -> str:
        """Derive state from recent chores or current phase."""
        today = datetime.now(tz=UTC).date()

        # 2. Current lifecycle phase
        for phase in CROP_PHASES:
            phase_data = self._phases.get(phase)
            if phase_data is None:
                continue
            start = phase_data.start
            end = phase_data.end
            if start and end:
                if start <= today <= end:
                    return phase
            elif start and today >= start:
                return phase

        return STATE_OK

    def update_registry(self) -> None:
        """Update registry with correct data."""
        erreg = er.async_get(self._hass)
        erreg.async_update_entity(self.entity_id)

    async def async_added_to_hass(self) -> None:
        """Register the entity in the entity registry once added to hass."""
        self.update_registry()
