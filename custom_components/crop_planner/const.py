"""Constants for integration_blueprint."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "crop"
CROP_PLANNER = "Crop Planner"
COORDINATOR = "coordinator"
COMPONENT = "component"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"
CROP_PLATFORM = "crop"
ICON = "mdi:leaf"

CONF_CROPS = "crops"
ATTR_CROP = "crop"
ATTR_NAME = "name"
ATTR_QUANTITY = "quantity"
ATTR_SOWING_DATE = "sowing_date"
ATTR_SPECIES = "species"

# Status
STATUS_DISABLED = "disabled"
STATUS_SUSPENDED = "suspended"
STATUS_BLOCKED = "blocked"
STATUS_INITIALISING = "initialising"
STATUS_PAUSED = "paused"
STATUS_DELAY = "delay"

# OpenPlantBook constants
DOMAIN_PLANTBOOK = "openplantbook"
OPB_GET = "get"
OPB_SEARCH = "search"
OPB_SEARCH_RESULT = "search_result"
OPB_PID = "pid"
OPB_DISPLAY_PID = "display_pid"
