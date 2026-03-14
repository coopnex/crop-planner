"""Tests for the CropPlannerCalendar entity."""

import datetime

import pytest
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crop.const import CONF_CROPS, CONF_TODOS, DOMAIN

_WINDOW_START = datetime.datetime(2026, 3, 1, tzinfo=datetime.UTC)
_WINDOW_END = datetime.datetime(2026, 4, 1, tzinfo=datetime.UTC)


@pytest.fixture
async def entry_with_todos(hass):
    """Config entry pre-loaded with a mix of todo items."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Crop Planner",
        data={
            CONF_CROPS: [],
            CONF_TODOS: [
                {
                    "uid": "todo-due-in-window",
                    "summary": "💧 Water tomatoes",
                    "status": "needs_action",
                    "due": "2026-03-20",
                    "description": "Check soil moisture",
                },
                {
                    "uid": "todo-completed",
                    "summary": "✂️ Pruned basil",
                    "status": "completed",
                    "due": "2026-03-15",
                    "description": None,
                },
                {
                    "uid": "todo-no-due",
                    "summary": "🌿 Fertilise pepper",
                    "status": "needs_action",
                    "due": None,
                    "description": None,
                },
                {
                    "uid": "todo-out-of-window",
                    "summary": "🧺 Harvest beans",
                    "status": "needs_action",
                    "due": "2026-05-10",
                    "description": None,
                },
            ],
        },
        unique_id="crop",
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    return entry


async def _get_events(hass, start, end):
    """Helper: retrieve calendar events via the HA service."""
    result = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": "calendar.crop_calendar",
            "start_date_time": start.isoformat(),
            "end_date_time": end.isoformat(),
        },
        blocking=True,
        return_response=True,
    )
    return result.get("calendar.crop_calendar", {}).get("events", [])


async def test_calendar_entity_created(hass, entry_with_todos):
    """The calendar entity is registered after setup."""
    assert hass.states.get("calendar.crop_calendar") is not None


async def test_todo_with_due_date_appears_as_event(hass, entry_with_todos):
    """An active todo with a due date inside the window produces a calendar event."""
    events = await _get_events(hass, _WINDOW_START, _WINDOW_END)
    summaries = [e["summary"] for e in events]
    assert "💧 Water tomatoes" in summaries


async def test_completed_todo_excluded_from_calendar(hass, entry_with_todos):
    """Completed todo items must not appear in calendar events."""
    events = await _get_events(hass, _WINDOW_START, _WINDOW_END)
    summaries = [e["summary"] for e in events]
    assert "✂️ Pruned basil" not in summaries


async def test_todo_without_due_date_excluded(hass, entry_with_todos):
    """Todos without a due date must not appear in calendar events."""
    events = await _get_events(hass, _WINDOW_START, _WINDOW_END)
    summaries = [e["summary"] for e in events]
    assert "🌿 Fertilise pepper" not in summaries


async def test_todo_outside_window_excluded(hass, entry_with_todos):
    """Todos with due dates outside the query window must not appear."""
    events = await _get_events(hass, _WINDOW_START, _WINDOW_END)
    summaries = [e["summary"] for e in events]
    assert "🧺 Harvest beans" not in summaries


async def test_event_description_preserved(hass, entry_with_todos):
    """The todo description is carried through to the calendar event."""
    events = await _get_events(hass, _WINDOW_START, _WINDOW_END)
    watering = next(e for e in events if e["summary"] == "💧 Water tomatoes")
    assert watering.get("description") == "Check soil moisture"
