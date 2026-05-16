"""Tests for Crop._compute_state phase detection logic."""

# ruff: noqa: SLF001

from datetime import date
from unittest.mock import MagicMock

from homeassistant.const import STATE_OK

from custom_components.crop.const import (
    PHASE_FLOWERING,
    PHASE_GERMINATION,
    PHASE_HARVEST,
    PHASE_SOWING,
)
from custom_components.crop.crop import Crop
from custom_components.crop.data import CropData, CropPhase


def _make_crop(*phase_tuples: tuple[str, date | None, date | None]) -> Crop:
    """Build a Crop with the given phases without touching HA internals."""
    phases = {
        name: CropPhase(start=start, end=end) for name, start, end in phase_tuples
    }
    config = CropData(id="test", name="Test", quantity=1, phases=phases)
    hass = MagicMock()
    crop = Crop.__new__(Crop)
    crop._hass = hass
    crop._attr_name = config.name
    crop._quantity = config.quantity
    crop._species = config.species
    crop._phases = config.phases
    crop._attr_entity_picture = None
    crop._unique_id = config.id
    crop._attr_unique_id = config.id
    return crop


# ── No phases ─────────────────────────────────────────────────────────────────


def test_no_phases_returns_ok():
    crop = _make_crop()
    assert crop._compute_state() == STATE_OK


# ── Bounded phases (start + end) ──────────────────────────────────────────────


def test_bounded_phase_today_inside_returns_phase(freezer):
    freezer.move_to("2026-04-15")
    crop = _make_crop(
        (PHASE_SOWING, date(2026, 4, 1), date(2026, 4, 30)),
    )
    assert crop._compute_state() == PHASE_SOWING


def test_bounded_phase_today_on_start_boundary(freezer):
    freezer.move_to("2026-04-01")
    crop = _make_crop(
        (PHASE_SOWING, date(2026, 4, 1), date(2026, 4, 30)),
    )
    assert crop._compute_state() == PHASE_SOWING


def test_bounded_phase_today_on_end_boundary(freezer):
    freezer.move_to("2026-04-30")
    crop = _make_crop(
        (PHASE_SOWING, date(2026, 4, 1), date(2026, 4, 30)),
    )
    assert crop._compute_state() == PHASE_SOWING


def test_bounded_phase_today_before_start_returns_ok(freezer):
    freezer.move_to("2026-03-31")
    crop = _make_crop(
        (PHASE_SOWING, date(2026, 4, 1), date(2026, 4, 30)),
    )
    assert crop._compute_state() == STATE_OK


def test_bounded_phase_today_after_end_returns_ok(freezer):
    freezer.move_to("2026-05-01")
    crop = _make_crop(
        (PHASE_SOWING, date(2026, 4, 1), date(2026, 4, 30)),
    )
    assert crop._compute_state() == STATE_OK


# ── Open-ended phases (start only) ────────────────────────────────────────────


def test_open_phase_today_on_start_returns_phase(freezer):
    freezer.move_to("2026-04-01")
    crop = _make_crop(
        (PHASE_SOWING, date(2026, 4, 1), None),
    )
    assert crop._compute_state() == PHASE_SOWING


def test_open_phase_today_after_start_returns_phase(freezer):
    freezer.move_to("2026-06-01")
    crop = _make_crop(
        (PHASE_SOWING, date(2026, 4, 1), None),
    )
    assert crop._compute_state() == PHASE_SOWING


def test_open_phase_today_before_start_returns_ok(freezer):
    freezer.move_to("2026-03-31")
    crop = _make_crop(
        (PHASE_SOWING, date(2026, 4, 1), None),
    )
    assert crop._compute_state() == STATE_OK


def test_phase_without_start_is_ignored(freezer):
    freezer.move_to("2026-05-01")
    crop = _make_crop(
        (PHASE_SOWING, None, date(2026, 4, 30)),
    )
    assert crop._compute_state() == STATE_OK


# ── Multiple phases — bounded takes priority over open-ended ──────────────────


def test_bounded_phase_wins_over_earlier_open_phase(freezer):
    """Open sowing should not shadow an active bounded flowering phase."""
    freezer.move_to("2026-05-16")
    crop = _make_crop(
        (PHASE_SOWING, date(2026, 3, 1), None),  # open, started
        (PHASE_FLOWERING, date(2026, 5, 1), date(2026, 7, 1)),  # bounded, active
    )
    assert crop._compute_state() == PHASE_FLOWERING


def test_later_open_phase_wins_over_earlier_open_phase(freezer):
    """The last started open-ended phase is returned when no bounded phase is active."""
    freezer.move_to("2026-06-01")
    crop = _make_crop(
        (PHASE_SOWING, date(2026, 3, 1), None),
        (PHASE_GERMINATION, date(2026, 4, 1), None),
        (PHASE_FLOWERING, date(2026, 5, 1), None),
    )
    assert crop._compute_state() == PHASE_FLOWERING


def test_ended_bounded_phase_does_not_block_later_open_phase(freezer):
    """An expired bounded phase should not prevent a later open phase from matching."""
    freezer.move_to("2026-06-01")
    crop = _make_crop(
        (PHASE_SOWING, date(2026, 3, 1), date(2026, 4, 30)),  # ended
        (PHASE_FLOWERING, date(2026, 5, 1), None),  # open, active
    )
    assert crop._compute_state() == PHASE_FLOWERING


def test_future_open_phase_does_not_match(freezer):
    """An open-ended phase whose start is in the future must not be returned."""
    freezer.move_to("2026-04-30")
    crop = _make_crop(
        (PHASE_SOWING, date(2026, 3, 1), None),  # started
        (PHASE_HARVEST, date(2026, 9, 1), None),  # not started yet
    )
    assert crop._compute_state() == PHASE_SOWING


def test_all_phases_defined_returns_correct_active_bounded(freezer):
    """Full phase set — only the phase whose range covers today is returned."""
    freezer.move_to("2026-05-16")
    crop = _make_crop(
        (PHASE_SOWING, date(2026, 3, 1), date(2026, 3, 31)),
        (PHASE_GERMINATION, date(2026, 4, 1), date(2026, 4, 30)),
        (PHASE_FLOWERING, date(2026, 5, 1), date(2026, 7, 31)),
        (PHASE_HARVEST, date(2026, 8, 1), date(2026, 9, 30)),
    )
    assert crop._compute_state() == PHASE_FLOWERING


def test_between_two_bounded_phases_returns_ok(freezer):
    """Gap between two bounded phases should yield STATE_OK."""
    freezer.move_to("2026-05-01")
    crop = _make_crop(
        (PHASE_SOWING, date(2026, 3, 1), date(2026, 3, 31)),
        (PHASE_FLOWERING, date(2026, 6, 1), date(2026, 8, 31)),
    )
    assert crop._compute_state() == STATE_OK
