# Crop Planner

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-0.1.2-blue?style=for-the-badge)](https://github.com/coopnex/crop-planner/releases)

A [Home Assistant](https://www.home-assistant.io/) custom integration for managing your crops. Track sowing dates, quantities, and species for each plant, view upcoming events in the HA calendar, and optionally enrich entries with images from the [OpenPlantbook](https://open.plantbook.io/) integration.

Each crop becomes a **sensor entity** (with name, quantity, sowing date, species, and a picture) and all crops are aggregated in a **calendar entity** so you can visualise your planting schedule from the HA dashboard.

---

## Installation

### Via HACS (recommended)

1. In Home Assistant, open **HACS → Integrations**.
2. Click the three-dot menu in the top-right corner and choose **Custom repositories**.
3. Add this repository URL with category **Integration**.
4. Find the **Crop Planner** card and click **Install**.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/crop` directory into your HA `custom_components/` folder.
2. Restart Home Assistant.

### Post-installation

Go to **Settings → Devices & Services → Add Integration** and search for **Crop Planner**.

> **Optional:** Install the [OpenPlantbook](https://github.com/open-plantbook/haintegration) integration first if you want automatic species images when creating crops.

---

## Usage

### Creating a crop

Call the `crop.create_crop` service (from **Developer Tools → Services** or an automation):

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Display name (e.g. `Tomate de colgar`) |
| `quantity` | Yes | Number of plants (1–50) |
| `sowing_date` | No | ISO date string, e.g. `2024-04-15` |
| `species` | No | Species name for OpenPlantbook lookup |

If `species` is provided and OpenPlantbook is installed, the entity picture is automatically populated from the plant database.

### Entities created

| Entity | Platform | Description |
|---|---|---|
| `sensor.crop_<name>` | `sensor` | One per crop — state is `ok`, attributes contain all crop data |
| `calendar.crop_planner` | `calendar` | Aggregated calendar with sowing dates |

---

## Development Setup

### Option 1 — Dev Container (recommended)

Open the repo in VS Code and choose **Reopen in Container**. The container:
- Installs all dependencies via `script/setup` + `script/bootstrap`
- Forwards port **8123** for the HA web UI
- Enables async debug mode (`PYTHONASYNCIODEBUG=1`)

### Option 2 — Local setup

**Requirements:** Python 3.13.2+, Home Assistant installed in a virtual environment.

```bash
# (First time) create and activate the virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dev dependencies
pip install -r requirements.txt

# (First time) initialise the config directory
hass --config config --script ensure_config

# Start Home Assistant with the integration loaded
script/develop
```

On subsequent sessions, just activate the existing venv before running any commands:

```bash
source .venv/bin/activate
```

The `script/develop` command sets `PYTHONPATH` so HA picks up `custom_components/crop` from the repo root and starts with `--debug`. The HA web UI is available at [http://localhost:8123](http://localhost:8123).

---

## Running Tests

Tests use [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component).

```bash
# (First time) install test dependencies
pip install -r requirements_test.txt

# Run all tests
pytest

# Run a specific file
pytest tests/test_init.py

# Run with verbose output
pytest -v
```

---

## Development Cheatsheet

```bash
# Start HA dev server
script/develop

# Run tests
pytest

# Lint changed Python files (Ruff + Pylint, relative to upstream/dev)
script/lint

# Check code formatting
script/check_format
```

> `script/lint` compares against `upstream/dev`. Add the upstream remote if needed:
> ```bash
> git remote add upstream https://github.com/coopnex/crop-planner.git
> ```

The formatter is **Ruff** (configured in `.ruff.toml`). Format on save is enabled in the dev container.

---

## Contributing

Pull requests are welcome. Please follow these steps:

1. Fork the repo and create a branch from `main`.
2. Make your changes and ensure `script/lint` passes.
3. Test manually with `script/develop`.
4. Open a pull request.

Bug reports and feature requests go to [GitHub Issues](https://github.com/coopnex/crop-planner/issues).

All contributions are licensed under the [MIT License](LICENSE).

---

## Roadmap

- **Todo-list platform** — expose crops as HA to-do items for checklist-style management
- **Harvest date tracking** — add expected harvest date based on species grow time from OpenPlantbook
- **Crop status lifecycle** — model states beyond `ok` (e.g. germinating, growing, harvested, failed)
- **Translations (i18n)** — add `strings.json` and translation files for multi-language support
- **Delete / archive service** — service call to remove or archive a crop entry
- **Notification automations** — blueprint for sowing-date reminders and harvest alerts
- **UI card** — custom Lovelace card for a visual garden overview
