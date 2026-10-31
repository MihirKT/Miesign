import json
import logging
import time
from functools import lru_cache
from io import BytesIO

from django.conf import settings
from google import genai
from google.genai import types
from PIL import Image, ImageDraw

from core.errors import AppError
from core.estimation import COMPONENT_TYPES, bbox

logger = logging.getLogger(__name__)
BOX_SCALE = 1000
DETECTION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "components": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "type": {"type": "STRING", "enum": list(COMPONENT_TYPES)},
                    "box_2d": {"type": "ARRAY", "items": {"type": "INTEGER"}, "minItems": 4, "maxItems": 4},
                    "floor": {"type": "INTEGER"},
                    "confidence": {"type": "NUMBER"},
                },
                "required": ["type", "box_2d", "floor"],
            },
        },
    },
    "required": ["components"],
}
RETRY_DELAY_SECONDS = 1
HARD_CONSTRAINTS = [
    "Keep the exact same camera angle, framing, perspective, lighting direction and image size.",
    "Do not move, add, remove or resize any window, door, balcony, pillar, wall, roof or gate.",
    "Keep sky, ground, trees, vehicles and neighbouring buildings unchanged.",
    "Change only the surface materials and colours listed in 'changes'.",
    "Each 'color' is an exact sRGB hex value: reproduce that hue and saturation faithfully under the photo's "
    "daylight; do not drift warmer, cooler, lighter or darker.",
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


def _json_call(contents, temperature=0.2, tools=None, expect=dict, schema=None):
    config = types.GenerateContentConfig(temperature=temperature, tools=tools)
    if tools is None:
        config.response_mime_type = "application/json"
        # A schema stops the model drifting into unrelated JSON (seen live: a car listing for a house photo).
        if schema is not None:
            config.response_schema = schema
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
        "Houses under construction, with bare plaster or unfinished walls, count as house exteriors. "
        "A low or slightly angled phone shot is fine as long as most of the front is visible. "
        "facade_visible is true only if most of the front of one residential building is in frame "
        "and not heavily blocked. issues lists ONLY problems that make the photo unusable for planning "
        "(not a house, front mostly hidden or cut off, far too dark or blurry); leave it empty otherwise. "
        "Minor imperfections such as cloudy light, a gate, plants or wires go in tips, not issues. "
        "issues and tips are short, plain English, at most 3 each; tips tell the person how to get a better photo."
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
    data, _ = _json_call([prompt, _image_part(image_bytes, mime)], temperature=0, expect=(dict, list),
                         schema=DETECTION_SCHEMA)
    # Vision models often answer with the bare array of boxes instead of the wrapping object.
    items = data if isinstance(data, list) else _list(data.get("components"))
    found = []
    for c in items:
        if not isinstance(c, dict):
            continue
        # Gemini names the field "box_2d" or "box" depending on the image; accept both.
        box = c.get("box_2d") or c.get("box")
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


def _spec_schema(material_ids, present_types):
    """Response schema for a DesignSpec; enums keep the model inside the catalog and the house's parts."""
    targets = [f"type:{t}" for t in present_types] or ["type:wall"]
    return {
        "type": "OBJECT",
        "properties": {
            "style": {"type": "STRING"},
            "palette": {"type": "ARRAY", "items": {"type": "STRING"}},
            "assignments": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "target": {"type": "STRING", "enum": targets},
                        "material_id": {"type": "STRING", "enum": list(material_ids)},
                        "color": {"type": "STRING", "nullable": True},
                        "finish": {"type": "STRING"},
                    },
                    "required": ["target", "material_id"],
                },
            },
            "keep_unchanged": {"type": "ARRAY", "items": {"type": "STRING", "enum": list(COMPONENT_TYPES)}},
            "notes": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
        "required": ["assignments"],
    }


COLOUR_RULES = (
    "Colours: every paint, texture or panel assignment gets a color as an exact #RRGGBB. "
    "If the homeowner gives a hex code, copy it verbatim; if they name a colour (e.g. terracotta, sage green, "
    "off-white), choose the standard hex for that name. Use null only for materials whose look is fixed "
    "(natural stone, glass, steel, wood-look). "
)


def parse_text(text, present_types, catalog):
    prompt = (
        "Convert a homeowner's exterior renovation request into a design spec. "
        f"Components present on the house: {present_types}. "
        f"Material catalog: {json.dumps(_catalog_brief(catalog.values()))}. "
        f"Reply with JSON only in this shape: {SPEC_SHAPE}. Rules: use only material_id values from the catalog; "
        "only target component types that are present and listed in that material's applies_to; "
        "if the request names a material that is not in the catalog, use the closest catalog material and say so in notes; "
        "put components the homeowner wants untouched in keep_unchanged. "
        f"{COLOUR_RULES}\n"
        f"Request: {text}"
    )
    data, _ = _json_call([prompt], schema=_spec_schema(catalog.keys(), present_types))
    return data


def recommend(answers, shortlist, present_types):
    prompt = (
        "You advise Indian homeowners on exterior renovation. Propose exactly 3 designs that differ in total cost "
        "(budget-friendly, balanced, premium) and suit their answers. "
        f"Answers: {json.dumps(answers)}. Components present: {present_types}. "
        f"Allowed materials: {json.dumps(_catalog_brief(shortlist))}. "
        'Reply with JSON only: {"designs": [{"name": string, "rationale": string (2 sentences: why these materials '
        f'suit the climate, budget and upkeep), "spec": {SPEC_SHAPE}}}]}}. '
        "Use only listed material_id values and only present component types that each material applies to. "
        f"Pick a coherent palette that follows the colour mood if one is given. {COLOUR_RULES}"
    )
    spec = _spec_schema([i["id"] for i in shortlist], present_types)
    schema = {
        "type": "OBJECT",
        "properties": {"designs": {"type": "ARRAY", "items": {
            "type": "OBJECT",
            "properties": {"name": {"type": "STRING"}, "rationale": {"type": "STRING"}, "spec": spec},
            "required": ["name", "rationale", "spec"],
        }}},
        "required": ["designs"],
    }
    data, _ = _json_call([prompt], temperature=0.6, schema=schema)
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


SWATCH_TILE = 200
SWATCH_GAP = 10
SWATCH_LABEL_HEIGHT = 40
SWATCH_NOTE = (
    "\nThe second image is the exact paint swatch card, one labelled tile per surface. Match each surface's "
    "colour to its swatch as it would look in daylight, keeping the swatch's saturation."
)


def build_swatch_card(spec):
    """PNG of labelled colour tiles for every coloured assignment, or None when nothing is coloured.

    Live tests showed text-only hex codes come out ~40 % less saturated; a reference image keeps
    hue and saturation much closer to what the homeowner picked.
    """
    tiles = [(a["target"].split(":", 1)[-1].replace("_", " "), a["color"])
             for a in spec.get("assignments", []) if a.get("color")]
    if not tiles:
        return None
    step = SWATCH_TILE + SWATCH_GAP
    card = Image.new("RGB", (step * len(tiles) + SWATCH_GAP, SWATCH_TILE + SWATCH_LABEL_HEIGHT + SWATCH_GAP), "white")
    draw = ImageDraw.Draw(card)
    for i, (label, colour) in enumerate(tiles):
        x = SWATCH_GAP + i * step
        draw.rectangle((x, SWATCH_GAP, x + SWATCH_TILE, SWATCH_GAP + SWATCH_TILE), fill=colour)
        draw.text((x, SWATCH_TILE + SWATCH_GAP * 2), f"{label}: {colour}", fill="black")
    buf = BytesIO()
    card.save(buf, format="PNG")
    return buf.getvalue()


def render(image_bytes, mime, prompt, swatch_png=None):
    config = types.GenerateContentConfig(response_modalities=["IMAGE"])
    contents = [_image_part(image_bytes, mime)]
    if swatch_png:
        contents += [_image_part(swatch_png, "image/png"), prompt + SWATCH_NOTE]
    else:
        contents.append(prompt)
    response = _generate(settings.MODEL_IMAGE, contents, config)
    for candidate in response.candidates or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                return inline.data
    raise AiUnavailable("The image model returned no picture. Try again.")
