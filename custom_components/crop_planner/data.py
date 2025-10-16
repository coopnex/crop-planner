"""Custom types for integration_blueprint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .coordinator import CropPlannerCoordinator


type CropPlannerConfigEntry = ConfigEntry[CropPlannerData]

@dataclass
class CropPlannerData:
    """Data for the Blueprint integration."""

    coordinator: CropPlannerCoordinator
    integration: Integration