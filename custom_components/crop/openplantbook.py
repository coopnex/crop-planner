"""Helper functions for calling the OpenPlantbook SDK directly."""

from __future__ import annotations

from typing import Any

from openplantbook_sdk import OpenPlantBookApi

from .const import LOGGER

REQUEST_TIMEOUT = 30


class OpenPlantbookHelper:
    """Thin wrapper around the OpenPlantbook SDK."""

    def __init__(self, client_id: str, secret: str) -> None:
        """Initialize with API credentials."""
        self._api = OpenPlantBookApi(client_id, secret)

    async def openplantbook_search(self, species: str) -> dict[str, Any] | None:
        """Search OPB and return raw SDK response, or None on failure."""
        if not species:
            return None
        try:
            return await self._api.async_plant_search(species)
        except Exception as ex:  # noqa: BLE001
            LOGGER.warning("OpenPlantbook search failed: %s", ex)
            return None

    async def openplantbook_get(self, pid: str) -> dict[str, Any] | None:
        """Get plant details from OpenPlantbook by PID."""
        if not pid:
            return None
        try:
            return await self._api.async_plant_detail_get(pid)
        except Exception as ex:  # noqa: BLE001
            LOGGER.warning("OpenPlantbook get failed for %s: %s", pid, ex)
            return None
