"""Constants for integration_blueprint."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "crop"
CROP_PLANNER = "Crop Planner"
COORDINATOR = "coordinator"
COMPONENT = "component"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"
CROP_PLATFORM = "crop"
ICON = "mdi:sprout"

CONF_CROPS = "crops"
CONF_TODOS = "todos"
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

# Crop lifecycle phases
PHASE_SOWING = "sowing"
PHASE_GERMINATION = "germination"
PHASE_FLOWERING = "flowering"
PHASE_HARVEST = "harvest"
CROP_PHASES = [PHASE_SOWING, PHASE_GERMINATION, PHASE_FLOWERING, PHASE_HARVEST]
PHASE_ICONS = {
    PHASE_SOWING: "🌱",
    PHASE_GERMINATION: "🌿",
    PHASE_FLOWERING: "🌸",
    PHASE_HARVEST: "🍂",
}

# OpenPlantBook constants
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"  # noqa: S105
OPB_PID = "pid"
OPB_DISPLAY_PID = "display_pid"
