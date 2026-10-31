from django.db import transaction
from django.utils import timezone

from core import ai
from core.errors import AppError
from core.estimation import COMPONENT_TYPES, default_scale, scale_from_component
from core.managers.projects import parse_id, primary_photo, read_bytes
from core.models import Component

MIN_REAL_FT = 1
MAX_REAL_FT = 100


def component_dicts(project):
    qs = Component.objects.filter(project_id=project.id, photo_id=project.primary_photo_id).order_by("created_at")
    return [{"id": str(c.id), "type": c.type, "quad": c.quad, "floor": c.floor, "source": c.source,
             "confidence": c.confidence} for c in qs]


def _refresh_default_scale(project, photo):
    if project.scale_source == "default":
        project.px_per_ft = default_scale(component_dicts(project), photo.height)
        project.save(update_fields=["px_per_ft", "updated_at"])


def detect(project):
    photo = primary_photo(project)
    found = ai.detect_structure(read_bytes(photo), photo.mime, photo.width, photo.height)
    with transaction.atomic():
        Component.objects.filter(project_id=project.id, photo_id=photo.id).update(deleted_at=timezone.now())
        Component.objects.bulk_create([
            Component(project_id=project.id, photo_id=photo.id, type=c["type"], quad=c["quad"],
                      floor=c["floor"], source="ai", confidence=c["confidence"])
            for c in found
        ])
    _refresh_default_scale(project, photo)
    return component_dicts(project)


def _clean_quad(quad, width, height):
    if not isinstance(quad, list) or len(quad) != 4:
        raise AppError("INVALID_REGION", "Each region needs exactly 4 corner points.")
    try:
        return [[min(max(float(x), 0), width), min(max(float(y), 0), height)] for x, y in quad]
    except (TypeError, ValueError):
        raise AppError("INVALID_REGION", "Region corners must be numbers.")


def save(project, items):
    photo = primary_photo(project)
    if not isinstance(items, list):
        raise AppError("INVALID_REGION", "components must be a list.")
    cleaned = []
    for item in items:
        if item.get("type") not in COMPONENT_TYPES:
            raise AppError("INVALID_REGION", f"Unknown part type '{item.get('type')}'.")
        cleaned.append({**item, "quad": _clean_quad(item.get("quad"), photo.width, photo.height)})

    with transaction.atomic():
        existing = {str(c.id): c for c in Component.objects.filter(project_id=project.id, photo_id=photo.id)}
        kept = set()
        for item in cleaned:
            current = existing.get(str(item.get("id")))
            if current:
                changed = current.type != item["type"] or current.quad != item["quad"]
                current.type, current.quad = item["type"], item["quad"]
                current.floor = int(item.get("floor") or 0)
                current.source = "user" if changed else current.source
                current.save()
                kept.add(str(current.id))
            else:
                Component.objects.create(project_id=project.id, photo_id=photo.id, type=item["type"],
                                         quad=item["quad"], floor=int(item.get("floor") or 0), source="user")
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
        component = Component.objects.filter(id=parse_id(component_id, "component_id"), project_id=project.id).first()
        if component is None:
            raise AppError("NOT_FOUND", "Part not found.", status=404)
        if not isinstance(real_height_ft, (int, float)) or not MIN_REAL_FT <= real_height_ft <= MAX_REAL_FT:
            raise AppError("INVALID_SCALE", f"Enter a height between {MIN_REAL_FT} and {MAX_REAL_FT} ft.")
        try:
            project.px_per_ft = scale_from_component(component.quad, real_height_ft)
        except ValueError:
            raise AppError("INVALID_SCALE", "That part has no height on the photo. Pick another one.")
        project.scale_source = "user"
    project.save()
    return project
