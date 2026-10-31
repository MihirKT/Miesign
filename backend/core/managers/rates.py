import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from core import ai
from core.catalog import city_tier, load_catalog
from core.errors import AppError
from core.models import RateCache, RateOverride

logger = logging.getLogger(__name__)
TIER_MULTIPLIER = {1: 1.2, 2: 1.0, 3: 0.85}
BOUND_LOW = 0.3
BOUND_HIGH = 3.0


def _fallback(item, tier):
    m = TIER_MULTIPLIER[tier]
    return {"material_rate": round(item["base_material_rate"] * m), "labor_rate": round(item["base_labor_rate"] * m),
            "source": "estimated", "sources": []}


def _within(value, base):
    return BOUND_LOW * base <= value <= BOUND_HIGH * base


def _validate_web(row, item):
    try:
        material_rate, labor_rate = float(row["material_rate"]), float(row["labor_rate"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (_within(material_rate, item["base_material_rate"]) and _within(labor_rate, item["base_labor_rate"])):
        return None
    return {"material_rate": round(material_rate), "labor_rate": round(labor_rate),
            "source": "web", "sources": [str(s) for s in row.get("sources", [])]}


def _fetch_and_cache(state, city, missing, tier, catalog):
    try:
        rows = ai.search_rates(state, city, missing)
    except ai.AiUnavailable:
        logger.warning("Rate search failed for %s, %s; using tier estimates", city, state)
        rows = []
    web = {}
    for row in rows:
        item = catalog.get(row.get("material_id"))
        valid = _validate_web(row, item) if item else None
        if valid:
            web[item["id"]] = valid
    cached = {}
    for item in missing:
        values = web.get(item["id"]) or _fallback(item, tier)
        obj, _ = RateCache.all_objects.update_or_create(
            state=state, city=city, material_id=item["id"],
            defaults={**values, "fetched_at": timezone.now(), "deleted_at": None},
        )
        cached[item["id"]] = obj
    return cached


def get_rates(state, city, project_id=None):
    catalog = load_catalog()
    tier = city_tier(state, city)
    fresh_after = timezone.now() - timedelta(days=settings.RATE_CACHE_DAYS)
    cached = {r.material_id: r for r in RateCache.objects.filter(state=state, city=city, fetched_at__gte=fresh_after)}
    missing = [item for mid, item in catalog.items() if mid not in cached]
    if missing and city:
        cached.update(_fetch_and_cache(state, city, missing, tier, catalog))

    result = {}
    for mid, item in catalog.items():
        c = cached.get(mid)
        if c:
            row = {"material_rate": c.material_rate, "labor_rate": c.labor_rate, "source": c.source,
                   "sources": c.sources, "fetched_at": c.fetched_at.isoformat()}
        else:
            row = {**_fallback(item, tier), "fetched_at": None}
        result[mid] = {**row, "material_id": mid, "rate_unit": item["rate_unit"]}

    if project_id:
        for o in RateOverride.objects.filter(project_id=project_id):
            row = result.get(o.material_id)
            if row is None:
                continue
            if o.material_rate is not None:
                row["material_rate"] = o.material_rate
            if o.labor_rate is not None:
                row["labor_rate"] = o.labor_rate
            row["source"] = "override"
    return result


def set_override(project_id, material_id, material_rate, labor_rate):
    if material_id not in load_catalog():
        raise AppError("UNKNOWN_MATERIAL", f"Material '{material_id}' is not in the catalog.")
    for value in (material_rate, labor_rate):
        if value is not None and (not isinstance(value, (int, float)) or value <= 0):
            raise AppError("INVALID_RATE", "Rates must be positive numbers.")
    RateOverride.all_objects.update_or_create(
        project_id=project_id, material_id=material_id,
        defaults={"material_rate": material_rate, "labor_rate": labor_rate, "deleted_at": None},
    )
