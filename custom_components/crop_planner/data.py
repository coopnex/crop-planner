"""Custom types for integration_blueprint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from crop_planner.const import LOGGER


def create_crop_data(data: Any) -> CropData:
    """Create a CropData instance from a dictionary."""
    LOGGER.debug("Creating CropData from data: %s", data)
    return CropData(
        id=data["id"],
        name=data["name"],
        quantity=1,
    )


@dataclass
class CropData:
    """Define an object to be stored in `entry.runtime_data`."""

    id: str
    name: str
    quantity: int
