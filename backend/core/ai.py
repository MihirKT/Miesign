import json
import logging
import time
from functools import lru_cache

from django.conf import settings
from google import genai
from google.genai import types

from core.errors import AppError
from core.estimation import COMPONENT_TYPES, bbox

logger = logging.getLogger(__name__)
BOX_SCALE = 1000
RETRY_DELAY_SECONDS = 1
HARD_CONSTRAINTS = [
    "Keep the exact same camera angle, framing, perspective, lighting direction and image size.",
    "Do not move, add, remove or resize any window, door, balcony, pillar, wall, roof or gate.",
    "Keep sky, ground, trees, vehicles and neighbouring buildings unchanged.",
    "Change only the surface materials and colours listed in 'changes'.",
]


class AiUnavailable(AppError):
    def __init__(self, message="The AI service did not respond. Try again in a minute."):
        super().__init__("AI_UNAVAILABLE", message, status=503)


def extract_json(text):
    if not text:
        raise ValueError("Empty model response.")
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        raise ValueError("No JSON found in model response.")
    value, _ = json.JSONDecoder().raw_decode(text[min(starts):])
    return value


def box_to_quad(box_2d, width, height):
    ymin, xmin, ymax, xmax = (min(max(v, 0), BOX_SCALE) / BOX_SCALE for v in box_2d)
    x0, x1 = round(xmin * width, 1), round(xmax * width, 1)
    y0, y1 = round(ymin * height, 1), round(ymax * height, 1)
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def build_render_prompt(spec, components, catalog, width, height):
    by_id = {str(c["id"]): c for c in components}
    changes = []
    for a in spec.get("assignments", []):
        item = catalog.get(a["material_id"])
        if item is None:
            continue
        target = a["target"]
        if target.startswith("type:"):
            where = f"every {target[5:].replace('_', ' ')} surface"
        else:
            component = by_id.get(target.split(":", 1)[1])
            if component is None:
                continue
            x0, y0, x1, y1 = bbox(component["quad"])
            where = (
                f"the {component['type'].replace('_', ' ')} inside the box "
                f"x {x0 / width:.0%}-{x1 / width:.0%}, y {y0 / height:.0%}-{y1 / height:.0%} of the image"
            )
        changes.append({"apply_to": where, "material": item["render_hint"],
                        "color": a.get("color"), "finish": a.get("finish")})
    payload = {
        "task": "Photorealistic exterior renovation of the house in the attached photo.",
        "hard_constraints": HARD_CONSTRAINTS,
        "style": spec.get("style", ""),
        "changes": changes,
        "keep_unchanged": spec.get("keep_unchanged", []),
        "output": "One photorealistic daylight photo, same resolution and framing as the input.",
    }
    return "Edit this photo of a house. Follow this JSON specification exactly:\n" + json.dumps(payload, indent=1)


MAX_SOURCES = 5


@lru_cache(maxsize=1)
def client():
    return genai.Client(vertexai=True, project=settings.GCP_PROJECT, location=settings.GCP_LOCATION)


def _generate(model, contents, config):
    last_error = None
    for attempt in range(2):
        try:
            return client().models.generate_content(model=model, contents=contents, config=config)
        except Exception as exc:  # SDK surfaces several error classes; retry once, then fail loudly
            last_error = exc
            logger.warning("Gemini call failed (attempt %s): %s", attempt + 1, exc)
            if attempt == 0:
                time.sleep(RETRY_DELAY_SECONDS)
    raise AiUnavailable() from last_error


def _list(value):
    return value if isinstance(value, list) else []


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _json_call(contents, temperature=0.2, tools=None, expect=dict):
    config = types.GenerateContentConfig(temperature=temperature, tools=tools)
    if tools is None:
        config.response_mime_type = "application/json"
    response = _generate(settings.MODEL_TEXT, contents, config)
    unreadable = AiUnavailable("The AI returned an unreadable answer. Try again.")
    try:
        data = extract_json(response.text)
    except (ValueError, TypeError) as exc:
        logger.warning("Unreadable Gemini JSON: %s", exc)
        raise unreadable from exc
    if not isinstance(data, expect):
        logger.warning("Gemini JSON had wrong type: %s", type(data).__name__)
        raise unreadable
    return data, response


def _image_part(image_bytes, mime):
    return types.Part.from_bytes(data=image_bytes, mime_type=mime)


def check_photo(image_bytes, mime):
    prompt = (
        "You check photos for a house-exterior renovation tool. Reply with JSON only: "
        '{"is_house_exterior": bool, "facade_visible": bool, "issues": [string], "tips": [string]}. '
        "facade_visible is true only if most of the front of one residential building is in frame "
        "and not heavily blocked. issues and tips are short, plain English, at most 3 each; "
        "tips tell the person how to retake the photo."
    )
    data, _ = _json_call([_image_part(image_bytes, mime), prompt], temperature=0)
    return {
        "is_house_exterior": bool(data.get("is_house_exterior")),
        "facade_visible": bool(data.get("facade_visible")),
        "issues": [str(i) for i in _list(data.get("issues"))][:3],
        "tips": [str(t) for t in _list(data.get("tips"))][:3],
    }


def detect_structure(image_bytes, mime, width, height):
    prompt = (
        "Detect the exterior building components of the main house in this photo. "
        f"Allowed types: {', '.join(COMPONENT_TYPES)}. Reply with JSON only: "
        '{"components": [{"type": string, "box_2d": [ymin, xmin, ymax, xmax], "floor": int, "confidence": number}]}. '
        "box_2d is normalised 0-1000. floor is 0 for ground floor, 1 for the first floor, and so on. "
        "Return one entry per visible wall face, window, door, balcony, pillar, parapet, gate, roof edge and railing. "
        "Ignore neighbouring buildings, vehicles, trees and people."
    )
    data, _ = _json_call([_image_part(image_bytes, mime), prompt], temperature=0)
    found = []
    for c in _list(data.get("components")):
        if not isinstance(c, dict):
            continue
        box = c.get("box_2d")
        if c.get("type") in COMPONENT_TYPES and isinstance(box, list) and len(box) == 4 and all(map(_number, box)):
            try:
                floor = int(c.get("floor") or 0)
            except (ValueError, TypeError):
                floor = 0
            confidence = c.get("confidence")
            found.append({
                "type": c["type"],
                "quad": box_to_quad(box, width, height),
                "floor": floor,
                "confidence": confidence if _number(confidence) else None,
            })
    return found


def _catalog_brief(items):
    return [{"material_id": i["id"], "name": i["name"], "applies_to": i["applies_to"],
             "maintenance": i["maintenance"], "budget": i["budget"]} for i in items]


SPEC_SHAPE = (
    '{"style": string, "palette": ["#RRGGBB"], "assignments": [{"target": "type:<component type>", '
    '"material_id": string, "color": "#RRGGBB" or null, "finish": string}], "keep_unchanged": [component type], '
    '"notes": [string]}'
)


def parse_text(text, present_types, catalog):
    prompt = (
        "Convert a homeowner's exterior renovation request into a design spec. "
        f"Components present on the house: {present_types}. "
        f"Material catalog: {json.dumps(_catalog_brief(catalog.values()))}. "
        f"Reply with JSON only in this shape: {SPEC_SHAPE}. Rules: use only material_id values from the catalog; "
        "only target component types that are present and listed in that material's applies_to; "
        "if the request names a material that is not in the catalog, use the closest catalog material and say so in notes; "
        "put components the homeowner wants untouched in keep_unchanged.\n"
        f"Request: {text}"
    )
    data, _ = _json_call([prompt])
    return data


def recommend(answers, shortlist, present_types):
    prompt = (
        "You advise Indian homeowners on exterior renovation. Propose exactly 3 designs that differ in total cost "
        "(budget-friendly, balanced, premium) and suit their answers. "
        f"Answers: {json.dumps(answers)}. Components present: {present_types}. "
        f"Allowed materials: {json.dumps(_catalog_brief(shortlist))}. "
        'Reply with JSON only: {"designs": [{"name": string, "rationale": string (2 sentences: why these materials '
        f'suit the climate, budget and upkeep), "spec": {SPEC_SHAPE}}}]}}. '
        "Use only listed material_id values and only present component types that each material applies to."
    )
    data, _ = _json_call([prompt], temperature=0.6)
    return [d for d in _list(data.get("designs")) if isinstance(d, dict)][:3]


def _grounding_uris(response):
    try:
        chunks = response.candidates[0].grounding_metadata.grounding_chunks or []
    except (AttributeError, IndexError, TypeError):
        return []
    return [c.web.uri for c in chunks if getattr(c, "web", None) and c.web.uri][:MAX_SOURCES]


def search_rates(state, city, items):
    wanted = [{"material_id": i["id"], "name": i["name"], "rate_unit": i["rate_unit"]} for i in items]
    prompt = (
        f"Find current average contractor rates in {city}, {state}, India, in INR, for these exterior renovation "
        "items. For each item give the material rate and the labour rate per the item's rate_unit "
        f"(sqft = per square foot, rft = per running foot). Items: {json.dumps(wanted)}. "
        'Reply with JSON only: {"rates": [{"material_id": string, "material_rate": number, '
        '"labor_rate": number, "sources": [url]}]}. Use numbers only, no ranges.'
    )
    data, response = _json_call([prompt], temperature=0, tools=[types.Tool(google_search=types.GoogleSearch())])
    fallback_sources = _grounding_uris(response)
    rows = []
    for r in _list(data.get("rates")):
        if isinstance(r, dict):
            own = [u for u in _list(r.get("sources")) if isinstance(u, str) and u.startswith("http")]
            rows.append({
                "material_id": r.get("material_id"),
                "material_rate": r.get("material_rate"),
                "labor_rate": r.get("labor_rate"),
                "sources": (fallback_sources or own)[:MAX_SOURCES],
            })
    return rows


def render(image_bytes, mime, prompt):
    config = types.GenerateContentConfig(response_modalities=["IMAGE"])
    response = _generate(settings.MODEL_IMAGE, [_image_part(image_bytes, mime), prompt], config)
    for candidate in response.candidates or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                return inline.data
    raise AiUnavailable("The image model returned no picture. Try again.")
