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


def default_scale(components, image_height):
    doors = [height_px(c["quad"]) for c in components if c["type"] == "door"]
    if doors:
        return mean(doors) / DEFAULT_DOOR_FT
    windows = [height_px(c["quad"]) for c in components if c["type"] == "window"]
    if windows:
        return mean(windows) / DEFAULT_WINDOW_FT
    return image_height / DEFAULT_VISIBLE_HEIGHT_FT


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


def _bbox_overlap(a, b):
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
            if smaller > 0 and _bbox_overlap(a["quad"], b["quad"]) / smaller > OVERLAP_WARN_RATIO:
                warnings.append("Two wall regions overlap; that area is counted twice. Adjust them on the Parts step.")
    return warnings
