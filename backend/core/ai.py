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
