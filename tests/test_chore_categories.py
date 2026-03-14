"""Unit tests for ChoreCategory enum and CHORE_CATEGORY_ICONS."""

from custom_components.crop.const import CHORE_CATEGORY_ICONS, ChoreCategory


def test_all_categories_have_icons():
    for category in ChoreCategory:
        assert category in CHORE_CATEGORY_ICONS, f"Missing icon for {category}"
        assert CHORE_CATEGORY_ICONS[category], f"Empty icon for {category}"


def test_category_values():
    assert ChoreCategory.WATERING == "watering"
    assert ChoreCategory.FERTILISING == "fertilising"
    assert ChoreCategory.PEST_INSPECTION == "pest_inspection"
    assert ChoreCategory.PRUNING == "pruning"
    assert ChoreCategory.HARVESTING == "harvesting"
    assert ChoreCategory.PLANTING == "planting"
    assert ChoreCategory.OTHER == "other"


def test_icons_are_distinct():
    icons = list(CHORE_CATEGORY_ICONS.values())
    assert len(icons) == len(set(icons)), "Each category should have a unique icon"


def test_category_icon_lookup_by_string():
    """Icon lookup should work with raw string values as well as enum members."""
    assert (
        CHORE_CATEGORY_ICONS.get("watering")
        == CHORE_CATEGORY_ICONS[ChoreCategory.WATERING]
    )
    assert (
        CHORE_CATEGORY_ICONS.get("harvesting")
        == CHORE_CATEGORY_ICONS[ChoreCategory.HARVESTING]
    )
