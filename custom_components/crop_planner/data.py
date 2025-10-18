"""Custom types for integration_blueprint."""

from __future__ import annotations

from dataclasses import dataclass
from email.mime import image
from typing import TYPE_CHECKING, Any

from crop_planner.const import LOGGER

if TYPE_CHECKING:
    from datetime import date


def create_crop_data(data: Any) -> CropData:
    """Create a CropData instance from a dictionary."""
    LOGGER.debug("Creating CropData from data: %s", data)
    return CropData(
        id=data["id"],
        name=data["name"],
        quantity=data["quantity"],
        species=data.get("species", None),
        sowing_date=data["sowing_date"],
        image_url=data.get("image_url", None),
    )


@dataclass
class CropData:
    """Define an object to be stored in `entry.runtime_data`."""

    id: str
    name: str
    quantity: int
    sowing_date: date
    species: str | None = None
    image_url: str | None = None
