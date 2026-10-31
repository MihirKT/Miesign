import hashlib
import json
import re

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import F

from core import ai
from core.catalog import load_catalog
from core.errors import AppError
from core.estimation import COMPONENT_TYPES
from core.managers.projects import parse_id, primary_photo, read_bytes
from core.managers.structure import component_dicts
from core.models import Design, Project

HEX = re.compile(r"#[0-9A-Fa-f]{6}")
MAX_PALETTE = 4
MAX_TEXT = 1000
MIN_TEXT = 3
MAX_DESIGNS_PER_REQUEST = 3
ANSWER_CHOICES = {
    "budget": {"low", "mid", "high"},
    "climate": {"coastal", "heavy_rain", "hot_dry", "moderate"},
    "style": {"modern", "traditional", "minimal", "luxe"},
    "maintenance": {"low", "medium"},
}
EXCLUDED_BUDGETS = {"low": {"high"}, "mid": set(), "high": set()}


def _as_list(value):
    return value if isinstance(value, list) else []


def _component_types(value):
    return [t for t in _as_list(value) if isinstance(t, str) and t in COMPONENT_TYPES]


def validate_spec(spec, catalog, components):
    if not isinstance(spec, dict) or not isinstance(spec.get("assignments"), list):
        raise AppError("INVALID_SPEC", "A design needs a list of assignments.")
    type_by_id = {str(c["id"]): c["type"] for c in components}
    present = set(type_by_id.values())
    clean, warnings = [], []
    for a in spec["assignments"]:
        if not isinstance(a, dict):
            continue
        material_id = a.get("material_id")
        target = str(a.get("target", ""))
        item = catalog.get(material_id) if isinstance(material_id, str) else None
        if item is None:
            warnings.append(f"Material '{a.get('material_id')}' is not in the catalog; skipped.")
            continue
        if target.startswith("type:"):
            ctype = target[len("type:"):]
            if ctype not in present:
                warnings.append(f"No {ctype.replace('_', ' ')} found on this house; {item['name']} skipped.")
                continue
        elif target.startswith("component:"):
            ctype = type_by_id.get(target[len("component:"):])
            if ctype is None:
                warnings.append(f"A selected part no longer exists; {item['name']} skipped.")
                continue
        else:
            warnings.append(f"Unknown target '{target}'; skipped.")
            continue
        if ctype not in item["applies_to"]:
            warnings.append(f"{item['name']} is not used on {ctype.replace('_', ' ')}; skipped.")
            continue
        color = a.get("color")
        clean.append({"target": target, "material_id": item["id"],
                      "color": color if isinstance(color, str) and HEX.fullmatch(color) else None,
                      "finish": str(a.get("finish") or "")[:40]})
    palette = [c for c in _as_list(spec.get("palette")) if isinstance(c, str) and HEX.fullmatch(c)][:MAX_PALETTE]
    keep = _component_types(spec.get("keep_unchanged"))
    return {"style": str(spec.get("style") or "")[:30], "palette": palette,
            "assignments": clean, "keep_unchanged": keep}, warnings


def validate_answers(answers):
    if not isinstance(answers, dict):
        raise AppError("INVALID_ANSWERS", "Answers must be an object.")
    clean = {}
    for key, choices in ANSWER_CHOICES.items():
        value = answers.get(key)
        if not isinstance(value, str) or value not in choices:
            raise AppError("INVALID_ANSWERS", f"Pick one of {sorted(choices)} for {key}.")
        clean[key] = value
    clean["color_mood"] = str(answers.get("color_mood") or "")[:60]
    clean["keep_unchanged"] = _component_types(answers.get("keep_unchanged"))
    return clean


def shortlist(answers, catalog):
    items = [
        i for i in catalog.values()
        if answers["climate"] in i["climates"]
        and not (answers["maintenance"] == "low" and i["maintenance"] == "high")
        and i["budget"] not in EXCLUDED_BUDGETS[answers["budget"]]
    ]
    return items or list(catalog.values())


def spec_hash(spec):
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()


def get_design(design_id):
    design = Design.objects.filter(id=parse_id(design_id, "design_id")).first()
    if design is None:
        raise AppError("NOT_FOUND", "Design not found.", status=404)
    return design


def _present_types(components):
    return sorted({c["type"] for c in components})


def from_text(project, text):
    text = str(text or "").strip()
    if not MIN_TEXT <= len(text) <= MAX_TEXT:
        raise AppError("INVALID_TEXT", f"Describe the design in {MIN_TEXT}-{MAX_TEXT} characters.")
    components, catalog = component_dicts(project), load_catalog()
    raw = ai.parse_text(text, _present_types(components), catalog)
    if not isinstance(raw, dict) or not isinstance(raw.get("assignments"), list):
        raise ai.AiUnavailable("The AI returned an unreadable design. Try again.")
    spec, warnings = validate_spec(raw, catalog, components)
    notes = [n[:200] for n in _as_list(raw.get("notes")) if isinstance(n, str)][:5]
    return Design.objects.create(project_id=project.id, name="Your description", mode="free_text",
                                 input={"text": text}, spec=spec, warnings=notes + warnings)


def recommend(project, answers):
    answers = validate_answers(answers)
    components, catalog = component_dicts(project), load_catalog()
    proposals = ai.recommend(answers, shortlist(answers, catalog), _present_types(components))
    if not isinstance(proposals, list):
        proposals = []
    created = []
    with transaction.atomic():
        for p in proposals[:MAX_DESIGNS_PER_REQUEST]:
            raw = p.get("spec") if isinstance(p, dict) else None
            if not isinstance(raw, dict) or not isinstance(raw.get("assignments"), list):
                continue
            spec, warnings = validate_spec(raw, catalog, components)
            spec["keep_unchanged"] = list(dict.fromkeys(answers["keep_unchanged"] + spec["keep_unchanged"]))
            created.append(Design.objects.create(
                project_id=project.id, name=str(p.get("name") or "Suggested design")[:60], mode="guided",
                input=answers, spec=spec, rationale=str(p.get("rationale") or "")[:600], warnings=warnings,
            ))
    if not created:
        raise AppError("NO_SUGGESTIONS", "We could not suggest designs. Try different answers or describe it yourself.")
    return created


def save(project, design_id, name, spec):
    spec, warnings = validate_spec(spec, load_catalog(), component_dicts(project))
    if design_id:
        design = get_design(design_id)
        if design.project_id != project.id:
            raise AppError("NOT_FOUND", "Design not found.", status=404)
        design.name, design.spec, design.warnings = str(name or design.name)[:60], spec, warnings
        design.save()
        return design
    return Design.objects.create(project_id=project.id, name=str(name or "My design")[:60], mode="manual",
                                 spec=spec, warnings=warnings)


def render(design):
    if not design.spec.get("assignments"):
        raise AppError("EMPTY_DESIGN", "This design has no materials yet. Pick materials on step 03 first.")
    current_hash = spec_hash(design.spec)
    if design.render_file and design.render_spec_hash == current_hash:
        return design
    project = Project.objects.get(id=design.project_id)
    claimed = Project.objects.filter(id=project.id, render_count__lt=settings.RENDER_CAP).update(
        render_count=F("render_count") + 1)
    if not claimed:
        raise AppError("RENDER_LIMIT", f"This project has used all {settings.RENDER_CAP} previews.", status=429)
    try:
        photo = primary_photo(project)
        prompt = ai.build_render_prompt(design.spec, component_dicts(project), load_catalog(), photo.width, photo.height)
        png = ai.render(read_bytes(photo), photo.mime, prompt)
    except Exception:
        Project.objects.filter(id=project.id).update(render_count=F("render_count") - 1)
        raise
    design.render_file.save(f"{design.id}-{current_hash[:8]}.png", ContentFile(png), save=False)
    design.render_spec_hash = current_hash
    design.save(update_fields=["render_file", "render_spec_hash", "updated_at"])
    return design
