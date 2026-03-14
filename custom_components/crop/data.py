"""Custom types for integration_blueprint."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Any

from .const import CROP_PHASES, LOGGER

if TYPE_CHECKING:
    pass


def _parse_date(value: str | None) -> date | None:
    if value:
        return date.fromisoformat(value)
    return None


def create_crop_data(data: Any) -> CropData:
    """Create a CropData instance from a dictionary."""
    LOGGER.debug("Creating CropData from data: %s", data)
    phases = {
        phase_name: CropPhase(
            start=_parse_date(phase_data.get("start")),
            end=_parse_date(phase_data.get("end")),
        )
        for phase_name, phase_data in data.get("phases", {}).items()
        if phase_name in CROP_PHASES
    }
    return CropData(
        id=data["id"],
        name=data["name"],
        quantity=data["quantity"],
        species=data.get("species", None),
        image_url=data.get("image_url", None),
        phases=phases,
    )


@dataclass
class CropPhase:
    """A named lifecycle phase with an optional date range."""

    start: date | None = None
    end: date | None = None

    def to_dict(self) -> dict[str, str | None]:
        """Serialize to a JSON-safe dict."""
        return {
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
        }


@dataclass
class CropData:
    """Define an object to be stored in `entry.runtime_data`."""

    id: str
    name: str
    quantity: int
    species: str | None = None
    image_url: str | None = None
    phases: dict[str, CropPhase] = field(default_factory=dict)
