"""Detected parts: run AI detection, clean the result, save user edits and manage the photo scale.

Miesign · Author: Mihir Kapildev Tiwari
"""

import math

from django.db import transaction
from django.utils import timezone

from core import ai
from core.errors import AppError
from core.estimation import COMPONENT_TYPES, bbox, bbox_overlap, default_scale, scale_from_component
from core.managers.projects import parse_id, primary_photo, read_bytes
from core.models import Component

MIN_REAL_FT = 1
MAX_REAL_FT = 100


def component_dicts(project):
    qs = Component.objects.filter(project_id=project.id, photo_id=project.primary_photo_id).order_by("created_at")
    return [{"id": str(c.id), "type": c.type, "quad": c.quad, "floor": c.floor, "source": c.source,
             "confidence": c.confidence} for c in qs]


# Only while the scale is still the default: a scale the user measured must survive re-detection and edits.
def _refresh_default_scale(project, photo):
    if project.scale_source == "default":
        project.px_per_ft = default_scale(component_dicts(project), photo.height)
        project.save(update_fields=["px_per_ft", "updated_at"])


NESTED_WALL_RATIO = 0.8  # a wall this much inside a bigger wall is a duplicate detection


def _box_area(quad):
    x0, y0, x1, y1 = bbox(quad)
    return max(x1 - x0, 0) * max(y1 - y0, 0)


def drop_nested_walls(found):
    """Remove wall boxes that sit mostly inside a larger wall, so their area isn't priced twice."""
    walls = sorted((c for c in found if c["type"] == "wall"), key=lambda c: _box_area(c["quad"]), reverse=True)
    kept = []
    for wall in walls:
        area = _box_area(wall["quad"])
        if area and any(bbox_overlap(wall["quad"], k["quad"]) / area > NESTED_WALL_RATIO for k in kept):
            continue
        kept.append(wall)
    return [c for c in found if c["type"] != "wall" or c in kept]


def ensure_wall(found):
    """Guarantee at least one wall so a facade is always priceable.

    Detection is not deterministic and occasionally returns only windows/railings. The
    fallback wall covers the area spanned by everything that was found; the user can
    adjust it on the Parts step like any other region.
    """
    if not found or any(c["type"] == "wall" for c in found):
        return found
    x0 = min(p[0] for c in found for p in c["quad"])
    y0 = min(p[1] for c in found for p in c["quad"])
    x1 = max(p[0] for c in found for p in c["quad"])
    y1 = max(p[1] for c in found for p in c["quad"])
    wall = {"type": "wall", "quad": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], "floor": 0, "confidence": None}
    return [wall, *found]


def detect(project):
    photo = primary_photo(project)
    found = drop_nested_walls(ensure_wall(ai.detect_structure(read_bytes(photo), photo.mime, photo.width, photo.height)))
    # Re-detect replaces the whole set atomically; a half-written list would price a facade with missing parts.
    with transaction.atomic():
        Component.objects.filter(project_id=project.id, photo_id=photo.id).update(deleted_at=timezone.now())
        Component.objects.bulk_create([
            Component(project_id=project.id, photo_id=photo.id, type=c["type"], quad=c["quad"],
                      floor=c["floor"], source="ai", confidence=c["confidence"])
            for c in found
        ])
    _refresh_default_scale(project, photo)
    return component_dicts(project)


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _clean_floor(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError, OverflowError):
        raise AppError("INVALID_REGION", "Floor must be a whole number.")


def _clean_quad(quad, width, height):
    if not isinstance(quad, list) or len(quad) != 4:
        raise AppError("INVALID_REGION", "Each region needs exactly 4 corner points.")
    try:
        pts = [[x, y] for x, y in quad]
        if not all(_is_number(v) for pt in pts for v in pt):
            raise ValueError
        return [[min(max(float(x), 0), width), min(max(float(y), 0), height)] for x, y in pts]
    except (TypeError, ValueError):
        raise AppError("INVALID_REGION", "Region corners must be finite numbers.")


def save(project, items):
    photo = primary_photo(project)
    if not isinstance(items, list):
        raise AppError("INVALID_REGION", "components must be a list.")
    cleaned = []
    for item in items:
        if not isinstance(item, dict):
            raise AppError("INVALID_REGION", "Each part must be an object.")
        if item.get("type") not in COMPONENT_TYPES:
            raise AppError("INVALID_REGION", f"Unknown part type '{item.get('type')}'.")
        cleaned.append({**item, "quad": _clean_quad(item.get("quad"), photo.width, photo.height),
                        "floor": _clean_floor(item.get("floor"))})

    # Full-list save: parts the client no longer sends are soft-deleted, so the client is the source of truth.
    with transaction.atomic():
        existing = {str(c.id): c for c in Component.objects.filter(project_id=project.id, photo_id=photo.id)}
        kept = set()
        for item in cleaned:
            current = existing.get(str(item.get("id")))
            if current:
                changed = current.type != item["type"] or current.quad != item["quad"]
                current.type, current.quad = item["type"], item["quad"]
                current.floor = item["floor"]
                # Keep "ai" if only the floor changed; "user" marks geometry the person actually edited.
                current.source = "user" if changed else current.source
                current.save()
                kept.add(str(current.id))
            else:
                Component.objects.create(project_id=project.id, photo_id=photo.id, type=item["type"],
                                         quad=item["quad"], floor=item["floor"], source="user")
        for cid, c in existing.items():
            if cid not in kept:
                c.soft_delete()
    _refresh_default_scale(project, photo)
    return component_dicts(project)


def set_scale(project, component_id=None, real_height_ft=None, use_default=False):
    photo = primary_photo(project)
    if use_default:
        project.scale_source = "default"
        project.px_per_ft = default_scale(component_dicts(project), photo.height)
    else:
        component = Component.objects.filter(id=parse_id(component_id, "component_id"), project_id=project.id,
                                              photo_id=project.primary_photo_id).first()
        if component is None:
            raise AppError("NOT_FOUND", "Part not found.", status=404)
        if not _is_number(real_height_ft) or not MIN_REAL_FT <= real_height_ft <= MAX_REAL_FT:
            raise AppError("INVALID_SCALE", f"Enter a height between {MIN_REAL_FT} and {MAX_REAL_FT} ft.")
        try:
            project.px_per_ft = scale_from_component(component.quad, real_height_ft)
        except ValueError:
            raise AppError("INVALID_SCALE", "That part has no height on the photo. Pick another one.")
        project.scale_source = "user"
    project.save()
    return project
