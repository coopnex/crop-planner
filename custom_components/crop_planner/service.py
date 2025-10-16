"""This module handles the HA service call interface"""
import voluptuous as vol


from datetime import datetime, date
from custom_components.crop_planner.coordinator import CropPlannerCoordinator
from homeassistant.core import ServiceCall, SupportsResponse, ServiceResponse, callback
from homeassistant.util import dt
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers import entity_registry as er
from homeassistant.const import (
    SERVICE_RELOAD,
    ATTR_ENTITY_ID,
)

from .const import (
    ATTR_QUANTITY,
    COMPONENT,
    DOMAIN,
    ATTR_NAME,
)

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
def register_component_services(
    component: EntityComponent, coordinator: CropPlannerCoordinator
) -> None:
    """Register the component"""
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
        # crop = Crop(hass, CropData(
        #     id=call.context.id,
        #     name=call.data[ATTR_NAME],
        #     quantity=call.data.get(ATTR_QUANTITY, 1),
        # ))
        # hass.data[DOMAIN][crop.unique_id] = crop
        # _component = hass.data[DOMAIN][COMPONENT]
        # await _component.async_add_entities([crop])
        # await hass.config_entries.async_forward_entry_setups(entry, [])
        # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
        # await cropPlanner.async_config_entry_first_refresh()

    async_register_admin_service(
        _component.hass,
        DOMAIN,
        SERVICE_RELOAD,
        reload_service_handler,
        schema=RELOAD_SERVICE_SCHEMA,
    )



        # erreg = er.async_get(hass)
        # await erreg.async_update_entity(crop.registry_entry.entity_id, device_id=crop.device_id)


    # @callback
    # async def get_info_service_handler(call: ServiceCall) -> ServiceResponse:
    #     """Return configuration"""
    #     # pylint: disable=unused-argument
    #     data = {}
    #     data["version"] = "1.0.0"
    #     data["crops"] = [],
    #     return data

    component.hass.services.async_register(
        DOMAIN,
        "create_crop",
        create_crop,
        CREATE_CROP_SCHEMA,
    )

    # component.hass.services.async_register(
    #     DOMAIN,
    #     SERVICE_GET_INFO,
    #     get_info_service_handler,
    #     {},
    #     supports_response=SupportsResponse.ONLY,
    # )