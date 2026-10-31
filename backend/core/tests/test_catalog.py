"""Tests that the catalog and city data are complete and consistent.

Miesign · Author: Mihir Kapildev Tiwari
"""

from core.catalog import city_tier, load_catalog, load_cities
from core.estimation import COMPONENT_TYPES

REQUIRED = {
    "id", "name", "category", "applies_to", "rate_unit", "qty_unit", "wastage_pct",
    "base_material_rate", "base_labor_rate", "durability_years", "maintenance",
    "budget", "climates", "styles", "render_hint",
}


def test_catalog_items_are_complete():
    catalog = load_catalog()
    assert len(catalog) >= 10
    for item_id, item in catalog.items():
        assert REQUIRED <= item.keys(), item_id
        assert set(item["applies_to"]) <= set(COMPONENT_TYPES), item_id
        assert item["rate_unit"] in {"sqft", "rft"}
        if item["qty_unit"] in {"L", "kg"}:
            assert item["coverage_per_unit"] > 0 and item["coats"] >= 1
        if item["qty_unit"] == "pcs":
            assert item["piece_sqft"] > 0


def test_cities_have_tiers():
    states = load_cities()
    assert sum(len(s["cities"]) for s in states) >= 80
    assert city_tier("Maharashtra", "Mumbai") == 1
    assert city_tier("Kerala", "Thrissur") == 3
    assert city_tier("Nowhere", "Unknown") == 2
