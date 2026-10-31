"""Tests rate priority, cache lifetimes, sanity bounds and overrides.

Miesign · Author: Mihir Kapildev Tiwari
"""

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from core import ai
from core.catalog import load_catalog
from core.errors import AppError
from core.managers import rates
from core.models import RateCache

PAINT = "exterior_emulsion"


def web_rows(material_rate, labor_rate):
    return [{"material_id": PAINT, "material_rate": material_rate, "labor_rate": labor_rate, "sources": ["https://a.in"]}]


@pytest.mark.django_db
def test_web_rate_within_bounds_is_used_and_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(ai, "search_rates", lambda s, c, items: calls.append(1) or web_rows(20, 11))

    result = rates.get_rates("Maharashtra", "Pune")
    assert result[PAINT]["material_rate"] == 20
    assert result[PAINT]["source"] == "web"
    rates.get_rates("Maharashtra", "Pune")
    assert calls == [1]  # second call served from cache


@pytest.mark.django_db
def test_out_of_bounds_web_rate_falls_back_to_tier(monkeypatch):
    monkeypatch.setattr(ai, "search_rates", lambda s, c, items: web_rows(9999, 11))
    result = rates.get_rates("Maharashtra", "Pune")  # tier 1
    base = load_catalog()[PAINT]
    assert result[PAINT]["source"] == "estimated"
    assert result[PAINT]["material_rate"] == round(base["base_material_rate"] * rates.TIER_MULTIPLIER[1])


@pytest.mark.django_db
def test_ai_failure_falls_back(monkeypatch):
    def boom(*args):
        raise ai.AiUnavailable()

    monkeypatch.setattr(ai, "search_rates", boom)
    result = rates.get_rates("Kerala", "Thrissur")
    assert all(r["source"] == "estimated" for r in result.values())


@pytest.mark.django_db
def test_stale_cache_is_refetched(monkeypatch):
    monkeypatch.setattr(ai, "search_rates", lambda s, c, items: web_rows(20, 11))
    rates.get_rates("Maharashtra", "Pune")
    RateCache.objects.update(fetched_at=timezone.now() - timedelta(days=31))
    monkeypatch.setattr(ai, "search_rates", lambda s, c, items: web_rows(22, 12))
    assert rates.get_rates("Maharashtra", "Pune")[PAINT]["material_rate"] == 22


@pytest.mark.django_db
def test_no_city_uses_tier_two_without_ai(monkeypatch):
    monkeypatch.setattr(ai, "search_rates", lambda *a: pytest.fail("should not call AI"))
    result = rates.get_rates("", "")
    assert result[PAINT]["material_rate"] == load_catalog()[PAINT]["base_material_rate"]


@pytest.mark.django_db
def test_override_wins(monkeypatch):
    monkeypatch.setattr(ai, "search_rates", lambda s, c, items: web_rows(20, 11))
    project_id = uuid.uuid4()
    rates.set_override(project_id, PAINT, material_rate=30, labor_rate=None)
    row = rates.get_rates("Maharashtra", "Pune", project_id=project_id)[PAINT]
    assert row["material_rate"] == 30
    assert row["labor_rate"] == 11
    assert row["source"] == "override"


@pytest.mark.django_db
def test_override_validation():
    with pytest.raises(AppError):
        rates.set_override(uuid.uuid4(), "nope", 10, 10)
    with pytest.raises(AppError):
        rates.set_override(uuid.uuid4(), PAINT, -5, None)


@pytest.mark.django_db
def test_estimated_rows_expire_after_estimate_window(monkeypatch):
    calls = []

    def boom(*args):
        calls.append(1)
        raise ai.AiUnavailable()

    monkeypatch.setattr(ai, "search_rates", boom)
    rates.get_rates("Kerala", "Thrissur")
    rates.get_rates("Kerala", "Thrissur")
    assert calls == [1]  # estimates cached
    RateCache.objects.update(fetched_at=timezone.now() - timedelta(hours=25))
    rates.get_rates("Kerala", "Thrissur")
    assert calls == [1, 1]


@pytest.mark.django_db
def test_web_rows_25_hours_old_still_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(ai, "search_rates", lambda s, c, items: calls.append(1) or web_rows(20, 11))
    rates.get_rates("Maharashtra", "Pune")
    RateCache.objects.filter(source="web").update(fetched_at=timezone.now() - timedelta(hours=25))
    result = rates.get_rates("Maharashtra", "Pune")
    assert calls == [1]
    assert result[PAINT]["source"] == "web"


@pytest.mark.django_db
@pytest.mark.parametrize("args", [(True, None), (None, True), (float("nan"), None), (None, float("inf")), (None, None)])
def test_set_override_rejects_bad_values(args):
    with pytest.raises(AppError):
        rates.set_override(uuid.uuid4(), PAINT, *args)


@pytest.mark.django_db
def test_malformed_ai_rows_do_not_raise(monkeypatch):
    good = {"material_id": PAINT, "material_rate": True, "labor_rate": 11, "sources": None}
    rows = ["junk", {"material_id": 123, "material_rate": 5, "labor_rate": 5}, good,
            {"material_id": "acp_panel", "material_rate": 70, "labor_rate": 70, "sources": None}]
    monkeypatch.setattr(ai, "search_rates", lambda s, c, items: rows)
    result = rates.get_rates("Maharashtra", "Pune")
    assert result[PAINT]["source"] == "estimated"  # bool rate invalid
    assert result["acp_panel"]["source"] == "web"  # sources=None tolerated
    assert result["acp_panel"]["sources"] == []
