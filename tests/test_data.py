"""Unit tests for the CropData dataclass and factory function."""

from datetime import date

import pytest

from custom_components.crop.data import CropData, CropPhase, create_crop_data


def test_crop_data_optional_fields_default():
    crop = CropData(id="1", name="Tomato", quantity=3)
    assert crop.species is None
    assert crop.image_url is None
    assert crop.phases == {}


def test_create_crop_data_minimal():
    data = {"id": "abc", "name": "Basil", "quantity": 2}
    crop = create_crop_data(data)
    assert crop.id == "abc"
    assert crop.name == "Basil"
    assert crop.quantity == 2
    assert crop.species is None
    assert crop.image_url is None
    assert crop.phases == {}


def test_create_crop_data_with_species_and_image():
    data = {
        "id": "xyz",
        "name": "Pepper",
        "quantity": 5,
        "species": "capsicum",
        "image_url": "https://example.com/pepper.jpg",
    }
    crop = create_crop_data(data)
    assert crop.species == "capsicum"
    assert crop.image_url == "https://example.com/pepper.jpg"


def test_create_crop_data_with_phases():
    data = {
        "id": "xyz",
        "name": "Tomato",
        "quantity": 3,
        "phases": {
            "sowing": {"start": "2026-03-01", "end": "2026-03-15"},
            "harvest": {"start": "2026-07-01", "end": None},
        },
    }
    crop = create_crop_data(data)
    assert "sowing" in crop.phases
    assert crop.phases["sowing"].start == date(2026, 3, 1)
    assert crop.phases["sowing"].end == date(2026, 3, 15)
    assert crop.phases["harvest"].start == date(2026, 7, 1)
    assert crop.phases["harvest"].end is None


def test_create_crop_data_ignores_unknown_phases():
    data = {
        "id": "abc",
        "name": "Basil",
        "quantity": 1,
        "phases": {"unknown_phase": {"start": "2026-01-01", "end": None}},
    }
    crop = create_crop_data(data)
    assert "unknown_phase" not in crop.phases


def test_crop_phase_to_dict():
    phase = CropPhase(start=date(2026, 3, 1), end=date(2026, 3, 15))
    assert phase.to_dict() == {"start": "2026-03-01", "end": "2026-03-15"}


def test_crop_phase_to_dict_none_dates():
    phase = CropPhase()
    assert phase.to_dict() == {"start": None, "end": None}


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("2026-03-01", None),
        (None, "2026-03-15"),
    ],
)
def test_crop_phase_partial_dates(start, end):
    data = {
        "id": "p",
        "name": "Pepper",
        "quantity": 1,
        "phases": {"sowing": {"start": start, "end": end}},
    }
    crop = create_crop_data(data)
    phase = crop.phases.get("sowing")
    assert phase is not None
    expected_start = date.fromisoformat(start) if start else None
    expected_end = date.fromisoformat(end) if end else None
    assert phase.start == expected_start
    assert phase.end == expected_end
