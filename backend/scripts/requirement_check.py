"""Live check: does a homeowner's free-text request come out right, colours included?

For each sample photo this runs the real pipeline (quality gate -> part detection ->
free-text design -> render -> estimate) and then measures how close the rendered wall
colour is to the colour the design asked for, as CIE76 delta-E in Lab space
split into hue difference, lightness and saturation. Lighting in the photo legitimately
changes lightness, so the verdict is driven by hue (< 15 degrees = the colour asked for)
and by how much of the requested saturation survived.

Usage (from backend/, venv active):
    python scripts/requirement_check.py
Costs a few Gemini calls per case on the configured Vertex project.

Miesign · Author: Mihir Kapildev Tiwari
"""
import os
import sys
import time
from pathlib import Path
import math

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from PIL import Image  # noqa: E402

from core.estimation import bbox  # noqa: E402
from core.managers import designs, estimates, photos, projects, structure  # noqa: E402

SAMPLES = Path(__file__).resolve().parent / "samples"
CASES = [
    ("user-house-1.jpg", "Punjab", "Ludhiana",
     "Warm terracotta texture paint (#C8553D) on all the walls, cream (#F3E9DC) on the parapet, "
     "black steel railing on the balcony."),
    ("user-house-2.jpg", "Gujarat", "Ahmedabad",
     "Soft sage green (#9CAF88) exterior paint on the walls, wooden WPC louvers on the top balcony, "
     "stainless steel railing."),
    ("user-house-3.jpg", "Uttar Pradesh", "Lucknow",
     "Modern look: charcoal grey (#36454F) ACP panels on the walls, white (#FFFFFF) paint on the pillars, "
     "glass railing on the balcony."),
]


def _srgb_to_lab(rgb):
    """sRGB 0-255 -> CIE Lab (D65). Small and dependency-free on purpose."""
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(float(c)) for c in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def _delta_e(rgb_a, rgb_b):
    la, lb = _srgb_to_lab(rgb_a), _srgb_to_lab(rgb_b)
    return sum((p - q) ** 2 for p, q in zip(la, lb)) ** 0.5


def _lch(rgb):
    lightness, a, b = _srgb_to_lab(rgb)
    return lightness, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def _hex_to_rgb(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


PALETTE_SIZE = 6  # dominant colours to split the wall area into
SAMPLE_SIDE = 48  # px per wall crop after downscaling; enough for clustering


def wall_colour_error(render_path, photo, components, target_hex):
    """Closest dominant wall colour in the render vs. the requested hex.

    Detected wall boxes also cover windows, slab shadows, railings and sky, so a plain
    median drifts. Instead the wall pixels are quantised into a few dominant colours and
    the one nearest the request is reported with its share of the wall area, which is
    how a person judges "is the wall that colour".
    """
    img = Image.open(render_path).convert("RGB")
    sx, sy = img.width / photo.width, img.height / photo.height
    crops = []
    for c in components:
        if c["type"] != "wall":
            continue
        x0, y0, x1, y1 = bbox(c["quad"])
        crop = img.crop((int(x0 * sx), int(y0 * sy), int(x1 * sx), int(y1 * sy)))
        if crop.width and crop.height:
            crops.append(crop.resize((SAMPLE_SIDE, SAMPLE_SIDE)))
    if not crops:
        return None, None, 0.0
    strip = Image.new("RGB", (SAMPLE_SIDE * len(crops), SAMPLE_SIDE))
    for i, crop in enumerate(crops):
        strip.paste(crop, (i * SAMPLE_SIDE, 0))
    quant = strip.quantize(colors=PALETTE_SIZE)
    palette = quant.getpalette()
    counts = quant.getcolors()
    total = sum(n for n, _ in counts)
    target = _hex_to_rgb(target_hex)
    target_lab = _srgb_to_lab(target)
    # Nearest by hue/chroma only (a*, b*): shade from the photo's lighting is not a wrong colour.
    best = min(
        ((tuple(palette[idx * 3: idx * 3 + 3]), n) for n, idx in counts),
        key=lambda item: math.dist(_srgb_to_lab(item[0])[1:], target_lab[1:]),
    )
    return best[0], _delta_e(best[0], target), best[1] / total


def run_case(filename, state, city, request):
    print(f"\n=== {filename} · {city} ===\nRequest: {request}")
    project = projects.update(projects.create(filename), state=state, city=city)
    photo = photos.upload(project, SimpleUploadedFile(filename, (SAMPLES / filename).read_bytes()))
    print("Photo:", "accepted" if photo.quality_ok else "REJECTED", photo.quality_report)
    if not photo.quality_ok:
        return
    project.refresh_from_db()
    parts = structure.detect(project)
    print("Parts:", {t: sum(c["type"] == t for c in parts) for t in sorted({c["type"] for c in parts})})
    design = designs.from_text(project, request)
    for a in design.spec["assignments"]:
        print(f"  {a['target']:<18} {a['material_id']:<24} {a['color'] or '-':<8} {a['finish']}")
    if design.warnings:
        print("  Notes:", design.warnings)
    start = time.time()
    design = designs.render(design)
    print(f"Render ({time.time() - start:.0f}s): {design.render_file.path}")
    wall = next((a for a in design.spec["assignments"] if a["target"] == "type:wall" and a["color"]), None)
    if wall:
        got, err, share = wall_colour_error(
            design.render_file.path, photo, structure.component_dicts(project), wall["color"])
        if got:
            want_l, want_c, want_h = _lch(_hex_to_rgb(wall["color"]))
            got_l, got_c, got_h = _lch(got)
            hue_diff = abs((got_h - want_h + 180) % 360 - 180) if want_c > 5 else 0.0
            saturation = got_c / want_c if want_c > 5 else 1.0
            verdict = "right colour" if hue_diff < 15 else "OFF"
            print(f"Wall colour: asked {wall['color']} got #{got[0]:02X}{got[1]:02X}{got[2]:02X} "
                  f"on {share:.0%} of wall area · hue off {hue_diff:.0f} deg · lightness {got_l:.0f} vs {want_l:.0f} "
                  f"· saturation {saturation:.0%} · delta-E {err:.1f} ({verdict})")
    est = estimates.for_design(design)
    print(f"Estimate: Rs {est['grand_total']:,}  scale={est['scale']['source']}")
    for line in est["lines"]:
        print(f"  {line['name']}: {line['measure']} {line['rate_unit']} ({line['rate_source']}) = Rs {line['total']:,}")


if __name__ == "__main__":
    for case in CASES:
        run_case(*case)
