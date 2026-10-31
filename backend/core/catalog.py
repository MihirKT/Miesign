"""Loads the material catalog and the state/city tier list from core/data/*.json and maps a city to its price tier.

Miesign · Author: Mihir Kapildev Tiwari
"""

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_TIER = 2


@lru_cache(maxsize=1)
def load_catalog():
    items = json.loads((DATA_DIR / "catalog.json").read_text(encoding="utf-8"))
    return {item["id"]: item for item in items}


@lru_cache(maxsize=1)
def load_cities():
    return json.loads((DATA_DIR / "cities.json").read_text(encoding="utf-8"))


def city_tier(state, city):
    for entry in load_cities():
        if entry["name"] == state:
            for c in entry["cities"]:
                if c["name"] == city:
                    return c["tier"]
    return DEFAULT_TIER
