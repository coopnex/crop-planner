"""Helper functions for the OpenPlantbook integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from async_timeout import timeout
from homeassistant.components.persistent_notification import (
    create as create_notification,
)

from .const import (
    ATTR_SPECIES,
    DOMAIN_PLANTBOOK,
    LOGGER,
    OPB_GET,
    OPB_SEARCH,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

REQUEST_TIMEOUT = 30


class OpenPlantbookHelper:
    """Helper functions for the plant integration."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    @property
    def has_openplantbook(self) -> bool:
        """Helper function to check if openplantbook is available."""
        LOGGER.debug(
            "%s in services? %s",
            DOMAIN_PLANTBOOK,
            DOMAIN_PLANTBOOK in self.hass.services.async_services(),
        )
        return DOMAIN_PLANTBOOK in self.hass.services.async_services()

    async def openplantbook_search(self, species: str) -> dict[str, Any] | None:
        """Search OPB and return list of result."""
        if not self.has_openplantbook:
            return None
        if not species or species == "":
            return None

        try:
            async with timeout(REQUEST_TIMEOUT):
                plant_search_result = await self.hass.services.async_call(
                    domain=DOMAIN_PLANTBOOK,
                    service=OPB_SEARCH,
                    service_data={"alias": species},
                    blocking=True,
                    return_response=True,
                )
        except TimeoutError:
            LOGGER.warning("Openplantbook request timed out")
            return None
        except Exception as ex:
            LOGGER.warning("Openplantbook does not work, error: %s", ex)
            return None
        if bool(plant_search_result):
            LOGGER.info("Result: %s", plant_search_result)

            return plant_search_result
        return None

    async def openplantbook_get(self, species: str) -> dict[str, Any] | None:
        """Get information about a plant species from OpenPlantbook."""
        if not self.has_openplantbook:
            LOGGER.error("Openplantbook not available")
            return None
        if not species or species == "":
            return None

        try:
            async with timeout(REQUEST_TIMEOUT):
                plant_get_result = await self.hass.services.async_call(
                    domain=DOMAIN_PLANTBOOK,
                    service=OPB_GET,
                    service_data={ATTR_SPECIES: species.lower()},
                    blocking=True,
                    return_response=True,
                )
        except TimeoutError:
            LOGGER.warning("Openplantbook request timed out")
        except Exception as ex:
            LOGGER.warning("Openplantbook does not work, error: %s", ex)
            return None
        if bool(plant_get_result):
            LOGGER.debug("Result for %s: %s", species, plant_get_result)
            return plant_get_result

        LOGGER.info("Did not find '%s' in OpenPlantbook", species)
        create_notification(
            hass=self.hass,
            title="Species not found",
            message=f"Could not find «{species}» in OpenPlantbook.",
        )
        return None
