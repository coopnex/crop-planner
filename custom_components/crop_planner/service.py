"""Service module handles the HA service call interface."""

from datetime import date, datetime

import voluptuous as vol
from homeassistant.const import (
    SERVICE_RELOAD,
)
from homeassistant.core import ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.service import async_register_admin_service

from .const import (
    ATTR_NAME,
    ATTR_QUANTITY,
    COORDINATOR,
    DOMAIN,
)
from .coordinator import CropPlannerCoordinator
from .crop import CropData


def _parse_dd_mmm(value: str) -> date | None:
    """Convert a date string in dd mmm format to a date object."""
    if isinstance(value, date):
        return value
    return datetime.strptime(f"{value} {datetime.today().year}", "%d %b %Y").date()


RELOAD_SERVICE_SCHEMA = vol.Schema({})
CREATE_CROP_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Optional(ATTR_QUANTITY): cv.positive_int,
    }
)
_component = None


def register_component_services(component: EntityComponent) -> None:
    """Register the component."""
    _component = component

    @callback
    async def reload_service_handler(call: ServiceCall) -> None:
        """Reload yaml entities."""
        # pylint: disable=unused-argument
        # pylint: disable=import-outside-toplevel
        # from .binary_sensor import async_reload_platform

        conf = await _component.async_prepare_reload(skip_reset=True)
        if conf is None or conf == {}:
            conf = {DOMAIN: {}}
        # coordinator.load(conf[DOMAIN])
        # await async_reload_platform(_component, coordinator)
        # coordinator.timer(dt.utcnow())
        # coordinator.clock.start()

    @callback
    async def create_crop(call: ServiceCall) -> None:
        """Reload schedule."""
        hass = call.hass
        coordinator: CropPlannerCoordinator = hass.data[DOMAIN][COORDINATOR]
        crop_data = CropData(
            id=call.context.id,
            name=call.data[ATTR_NAME],
            quantity=call.data.get(ATTR_QUANTITY, 1),
        )

        new_data = {
            "crops": [
                *coordinator.config_entry.data.get("crops", []),
                crop_data.__dict__,
            ],
        }

        hass.config_entries.async_update_entry(
            coordinator.config_entry, data=new_data, unique_id=call.context.id
        )

    async_register_admin_service(
        _component.hass,
        DOMAIN,
        SERVICE_RELOAD,
        reload_service_handler,
        schema=RELOAD_SERVICE_SCHEMA,
    )

    component.hass.services.async_register(
        DOMAIN,
        "create_crop",
        create_crop,
        CREATE_CROP_SCHEMA,
    )
