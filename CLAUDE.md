# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Home Assistant custom integration** for crop planning. It allows users to manage crop entries (planting dates, quantities, species) with optional integration to the [OpenPlantbook](https://open.plantbook.io/) API for species data and imagery. The integration exposes crop entries as Home Assistant entities and calendar events.

- **Domain:** `crop`
- **Minimum HA version:** 2025.10.2
- **Python:** 3.13+
- **Single config entry** (only one instance allowed)

## Development Commands

```bash
# Start Home Assistant dev server with this integration loaded
script/develop

# Lint changed Python files (runs Ruff + Pylint)
script/lint

# Check code formatting
script/check_format
```

The `script/develop` command sets up a local HA instance in `config/` and launches it with debug logging. This is the primary way to manually test the integration.

## Architecture

### Component Layout (`custom_components/crop/`)

```
__init__.py        # Integration setup, async_setup / async_setup_entry
coordinator.py     # CropPlannerCoordinator (DataUpdateCoordinator) — central state hub
config_flow.py     # UI config flow for adding the integration
crop.py            # CropEntity (Entity) — one entity per crop
calendar.py        # CropPlannerCalendar (CalendarEntity) — calendar platform
service.py         # Service handlers: create_crop, reload
data.py            # CropData dataclass and factory
openplantbook.py   # Helper to call the openplantbook integration
const.py           # DOMAIN, constants, logger
services.yaml      # Service schemas exposed to HA UI/automations
manifest.json      # Integration metadata (version, dependencies)
```

### Data Flow

1. **Config entry** stores a list of crop dicts (`id`, `name`, `quantity`, `sowing_date`, `species?`, `image_url?`).
2. **`async_setup_entry`** creates a `CropPlannerCoordinator`, builds `CropEntity` objects from config, and registers them plus the calendar platform.
3. **`create_crop` service** appends a new crop to the config entry; an update listener triggers a reload which re-runs `async_setup_entry`.
4. **`CropPlannerCoordinator`** owns the device registry entry and is the reference point for all entities to associate their device.
5. **`OpenPlantbookHelper`** optionally calls the `openplantbook` integration (after-dependency) to fetch species image URLs.

### Key Design Points

- All crop state is persisted in the config entry (`hass.config_entries`), not in files or a database.
- The coordinator does not poll; it exists primarily for device association and as a shared data container.
- Entity pictures fall back to `/local/crop_planner/default.png` when no `image_url` is set.
- Services are registered at the domain level in `async_setup()` (YAML-based setup path), not per config entry.

## Linting Configuration

Ruff and Pylint are configured in `pyproject.toml` and `.ruff.toml`. Max cyclomatic complexity is 25. The lint script only checks files changed since the merge-base, so run it regularly during development.
