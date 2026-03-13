"""Unit tests for the CropData dataclass and factory function."""

from custom_components.crop.data import CropData, create_crop_data


def test_crop_data_optional_fields_default_to_none():
    crop = CropData(id="1", name="Tomato", quantity=3, sowing_date="2024-04-15")
    assert crop.species is None
    assert crop.image_url is None


def test_create_crop_data_minimal():
    data = {"id": "abc", "name": "Basil", "quantity": 2, "sowing_date": "2024-05-01"}
    crop = create_crop_data(data)
    assert crop.id == "abc"
    assert crop.name == "Basil"
    assert crop.quantity == 2
    assert crop.sowing_date == "2024-05-01"
    assert crop.species is None
    assert crop.image_url is None


def test_create_crop_data_with_species_and_image():
    data = {
        "id": "xyz",
        "name": "Pepper",
        "quantity": 5,
        "sowing_date": "2024-06-01",
        "species": "capsicum",
        "image_url": "https://example.com/pepper.jpg",
    }
    crop = create_crop_data(data)
    assert crop.species == "capsicum"
    assert crop.image_url == "https://example.com/pepper.jpg"
