"""Pure estimation maths: polygon areas, scale, wall-minus-openings, quantities with wastage and the priced lines. No I/O, so every formula is unit-tested without a database.

Miesign · Author: Mihir Kapildev Tiwari
"""

import math
from statistics import mean

COMPONENT_TYPES = ["wall", "window", "door", "balcony", "pillar", "parapet", "gate", "roof_edge", "railing"]

OPENING_TYPES = {"window", "door"}
NON_SURFACE_TYPES = {"window", "door"}
DEFAULT_DOOR_FT = 7.0
DEFAULT_WINDOW_FT = 4.0
# A typical Indian independent house front shows ~2 storeys (~20 ft) of facade.
DEFAULT_VISIBLE_HEIGHT_FT = 20.0
PILLAR_FACES = 4
OVERLAP_WARN_RATIO = 0.2


def polygon_area_px(quad):
    total = 0.0
    for i, (x1, y1) in enumerate(quad):
        x2, y2 = quad[(i + 1) % len(quad)]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2


def bbox(quad):
    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    return min(xs), min(ys), max(xs), max(ys)


def width_px(quad):
    x0, _, x1, _ = bbox(quad)
    return x1 - x0


def height_px(quad):
    _, y0, _, y1 = bbox(quad)
    return y1 - y0


def centroid(quad):
    return sum(p[0] for p in quad) / len(quad), sum(p[1] for p in quad) / len(quad)


def point_in_polygon(pt, poly):
    x, y = pt
    inside = False
    for i, (x1, y1) in enumerate(poly):
        x2, y2 = poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def area_sqft(quad, px_per_ft):
    if px_per_ft <= 0:
        return 0.0
    return polygon_area_px(quad) / (px_per_ft ** 2)


def scale_from_component(quad, real_height_ft):
    h = height_px(quad)
    if h <= 0 or real_height_ft <= 0:
        raise ValueError("Height in pixels and real height must both be positive.")
    return h / real_height_ft


# No user measurement: infer feet-per-pixel from a part whose real size is standard, door first because
# it varies least, then window, then assume the frame shows about 20 ft of facade.
def default_scale(components, image_height):
    doors = [height_px(c["quad"]) for c in components if c["type"] == "door"]
    if doors:
        return mean(doors) / DEFAULT_DOOR_FT
    windows = [height_px(c["quad"]) for c in components if c["type"] == "window"]
    if windows:
        return mean(windows) / DEFAULT_WINDOW_FT
    return image_height / DEFAULT_VISIBLE_HEIGHT_FT


# Walls are net of openings so paint is not priced on windows and doors; pillars count 4 faces because
# only one face is visible in the photo; railings are priced by running length, which is the box width.
def measure(component, components, px_per_ft, rate_unit):
    quad = component["quad"]
    if rate_unit == "rft":
        return width_px(quad) / px_per_ft if px_per_ft > 0 else 0.0
    area = area_sqft(quad, px_per_ft)
    if component["type"] == "pillar":
        return area * PILLAR_FACES
    if component["type"] == "wall":
        for other in components:
            if other["type"] in OPENING_TYPES and point_in_polygon(centroid(other["quad"]), quad):
                area -= area_sqft(other["quad"], px_per_ft)
        return max(area, 0.0)
    return area


def bbox_overlap(a, b):
    ax0, ay0, ax1, ay1 = bbox(a)
    bx0, by0, bx1, by1 = bbox(b)
    w = min(ax1, bx1) - max(ax0, bx0)
    h = min(ay1, by1) - max(ay0, by0)
    return w * h if w > 0 and h > 0 else 0.0


def walls_overlap_warnings(components):
    walls = [c for c in components if c["type"] == "wall"]
    warnings = []
    for i, a in enumerate(walls):
        for b in walls[i + 1:]:
            smaller = min(polygon_area_px(a["quad"]), polygon_area_px(b["quad"]))
            if smaller > 0 and bbox_overlap(a["quad"], b["quad"]) / smaller > OVERLAP_WARN_RATIO:
                warnings.append("Two wall regions overlap; that area is counted twice. Adjust them on the Parts step.")
    return warnings

BASE_ASSUMPTIONS = [
    "Only the facade visible in the photo is measured.",
    "Wall areas exclude windows and doors whose centre lies inside the wall.",
    "Pillars are treated as square columns: 4 faces of the visible width.",
    "Railing length equals the visible width of the railing or balcony.",
    "Rates are advisory averages; confirm with a local contractor.",
]
DEFAULT_SCALE_ASSUMPTION = (
    "Scale was assumed from a standard 7 ft door or 4 ft window (or a 20 ft high front). "
    "Enter one real measurement on the Parts step for a better estimate."
)


# Wastage is applied in the cost too (see estimate) so the quantity to buy and the money agree.
def quantity(item, measure_value):
    factor = 1 + item["wastage_pct"] / 100
    unit = item["qty_unit"]
    if unit in ("L", "kg"):
        return round(measure_value * item["coats"] / item["coverage_per_unit"] * factor, 1)
    if unit == "pcs":
        return math.ceil(measure_value / item["piece_sqft"] * factor)
    return round(measure_value * factor, 1)


def resolve_assignments(components, spec):
    by_component, by_type = {}, {}
    for a in spec.get("assignments", []):
        target = a["target"]
        if target.startswith("component:"):
            by_component[target.split(":", 1)[1]] = a
        elif target.startswith("type:"):
            by_type[target.split(":", 1)[1]] = a
    keep = set(spec.get("keep_unchanged", []))
    pairs = []
    for c in components:
        if c["type"] in NON_SURFACE_TYPES or c["type"] in keep:
            continue
        a = by_component.get(str(c["id"])) or by_type.get(c["type"])
        if a:
            pairs.append((c, a))
    return pairs


def estimate(components, spec, catalog, rates, px_per_ft, scale_source):
    grouped, warnings = {}, []
    for c, a in resolve_assignments(components, spec):
        item = catalog.get(a["material_id"])
        if item is None:
            warnings.append(f"Material '{a['material_id']}' is not in the catalog; skipped.")
            continue
        if c["type"] not in item["applies_to"]:
            warnings.append(f"{item['name']} is not used on {c['type'].replace('_', ' ')}; skipped.")
            continue
        group = grouped.setdefault(item["id"], {"measure": 0.0, "targets": {}})
        group["measure"] += measure(c, components, px_per_ft, item["rate_unit"])
        group["targets"][c["type"]] = group["targets"].get(c["type"], 0) + 1

    lines, grand_total = [], 0
    for material_id, group in grouped.items():
        item, rate = catalog[material_id], rates[material_id]
        measure_value = round(group["measure"], 1)
        material_cost = round(measure_value * (1 + item["wastage_pct"] / 100) * rate["material_rate"])
        labor_cost = round(measure_value * rate["labor_rate"])
        total = material_cost + labor_cost
        grand_total += total
        lines.append({
            "category": item["category"],
            "material_id": material_id,
            "name": item["name"],
            "targets": [f"{t}×{n}" for t, n in group["targets"].items()],
            "measure": measure_value,
            "rate_unit": item["rate_unit"],
            "quantity": quantity(item, measure_value),
            "qty_unit": item["qty_unit"],
            "wastage_pct": item["wastage_pct"],
            "material_rate": rate["material_rate"],
            "labor_rate": rate["labor_rate"],
            "rate_source": rate["source"],
            "material_cost": material_cost,
            "labor_cost": labor_cost,
            "total": total,
        })

    assumptions = list(BASE_ASSUMPTIONS)
    if scale_source == "default":
        assumptions.insert(0, DEFAULT_SCALE_ASSUMPTION)
    return {
        "scale": {"px_per_ft": round(px_per_ft, 2), "source": scale_source},
        "lines": lines,
        "grand_total": grand_total,
        "assumptions": assumptions,
        "warnings": warnings,
    }
