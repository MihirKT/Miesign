"""Live end-to-end run against Vertex. Usage: python scripts/smoke_ai.py scripts/samples/house1.png Maharashtra Pune"""
import json
import os
import sys
import time
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402

from core.managers import designs, estimates, photos, projects, structure  # noqa: E402


def step(label, fn):
    start = time.time()
    result = fn()
    print(f"[{time.time() - start:5.1f}s] {label}")
    return result


def main(path, state, city):
    project = projects.update(projects.create("Smoke"), state=state, city=city)
    data = Path(path).read_bytes()
    photo = step("upload + quality gate", lambda: photos.upload(project, SimpleUploadedFile(Path(path).name, data)))
    print(json.dumps({"ok": photo.quality_ok, **photo.quality_report}, indent=1))
    if not photo.quality_ok:
        return
    project.refresh_from_db()
    found = step("detect", lambda: structure.detect(project))
    print({t: sum(c["type"] == t for c in found) for t in sorted({c["type"] for c in found})})
    project.refresh_from_db()
    print("px_per_ft (default):", round(project.px_per_ft or 0, 2))
    design = step("free text", lambda: designs.from_text(
        project, "Grey texture paint on walls, slate cladding on pillars, glass railing on balconies"))
    print(json.dumps(design.spec, indent=1), design.warnings)
    guided = step("recommend", lambda: designs.recommend(project, {
        "budget": "mid", "climate": "heavy_rain", "style": "modern", "maintenance": "low"}))
    for d in guided:
        print(" -", d.name, "|", d.rationale[:140], "|", [a["material_id"] for a in d.spec["assignments"]])
    design = step("render", lambda: designs.render(design))
    print("render:", design.render_file.path)
    est = step("estimate (incl. rate search)", lambda: estimates.for_design(design))
    print(json.dumps({k: est[k] for k in ("scale", "grand_total", "warnings")}, indent=1))
    for line in est["lines"]:
        print(f"  {line['name']}: {line['measure']} {line['rate_unit']} @ {line['material_rate']}+{line['labor_rate']}"
              f" ({line['rate_source']}) = {line['total']}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
