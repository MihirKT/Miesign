from io import BytesIO

import pytest
from PIL import Image
from rest_framework.test import APIClient

from core import ai

GOOD = {"is_house_exterior": True, "facade_visible": True, "issues": [], "tips": []}
PARTS = [
    {"type": "wall", "quad": [[0, 0], [1000, 0], [1000, 800], [0, 800]], "floor": 0, "confidence": 0.9},
    {"type": "door", "quad": [[100, 520], [160, 520], [160, 800], [100, 800]], "floor": 0, "confidence": 0.8},
    {"type": "railing", "quad": [[0, 300], [400, 300], [400, 340], [0, 340]], "floor": 1, "confidence": 0.7},
]


def jpeg():
    buf = BytesIO()
    Image.effect_noise((1000, 800), 64).convert("RGB").save(buf, format="JPEG")
    buf.seek(0)
    buf.name = "house.jpg"
    return buf


def png_bytes():
    buf = BytesIO()
    Image.new("RGB", (100, 80), (120, 130, 140)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(ai, "check_photo", lambda b, m: GOOD)
    monkeypatch.setattr(ai, "detect_structure", lambda b, m, w, h: PARTS)
    monkeypatch.setattr(ai, "search_rates", lambda s, c, items: [])
    monkeypatch.setattr(ai, "render", lambda b, m, p: png_bytes())
    monkeypatch.setattr(ai, "parse_text", lambda t, types, cat: {
        "assignments": [{"target": "type:wall", "material_id": "texture_paint", "color": "#D9D4CC"},
                        {"target": "type:railing", "material_id": "glass_railing"}]})
    return APIClient()


@pytest.mark.django_db
def test_full_flow(api):
    project = api.post("/api/project/create", {"name": "Test"}, format="json").json()
    pid = project["id"]

    assert api.post(f"/api/project/update?id={pid}", {"state": "Maharashtra", "city": "Pune"},
                    format="json").status_code == 200
    project = api.post(f"/api/photo/upload?project_id={pid}", {"file": jpeg()}, format="multipart").json()
    assert project["photos"][0]["quality_ok"]

    project = api.post(f"/api/structure/detect?project_id={pid}").json()
    assert len(project["components"]) == 3
    door = next(c for c in project["components"] if c["type"] == "door")
    project = api.post(f"/api/scale/set?project_id={pid}", {"component_id": door["id"], "real_height_ft": 7},
                       format="json").json()
    assert project["scale_source"] == "user"

    designs = api.post(f"/api/design/from-text?project_id={pid}", {"text": "grey texture, glass railing"},
                       format="json").json()["designs"]
    did = designs[0]["id"]

    rendered = api.post(f"/api/design/render?id={did}").json()
    assert rendered["render_url"].endswith(".png")

    estimate = api.get(f"/api/estimate?design_id={did}").json()
    assert estimate["grand_total"] > 0
    assert {line["material_id"] for line in estimate["lines"]} == {"texture_paint", "glass_railing"}

    rates = api.post(f"/api/rates/override?project_id={pid}",
                     {"material_id": "texture_paint", "material_rate": 50}, format="json").json()["rates"]
    assert next(r for r in rates if r["material_id"] == "texture_paint")["source"] == "override"
    assert api.get(f"/api/estimate?design_id={did}").json()["grand_total"] > estimate["grand_total"]

    pdf = api.get(f"/api/report?design_id={did}")
    assert pdf["Content-Type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")


@pytest.mark.django_db
def test_errors_have_shape(api):
    missing = api.get("/api/project?id=00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"

    bad = api.get("/api/project?id=nope")
    assert bad.status_code == 400

    pid = api.post("/api/project/create", {}, format="json").json()["id"]
    no_photo = api.post(f"/api/structure/detect?project_id={pid}")
    assert no_photo.status_code == 400
    assert no_photo.json()["error"]["code"] == "NO_PHOTO"


@pytest.mark.django_db
def test_detect_empty_still_allows_manual_parts(api, monkeypatch):
    monkeypatch.setattr(ai, "detect_structure", lambda b, m, w, h: [])
    pid = api.post("/api/project/create", {}, format="json").json()["id"]
    api.post(f"/api/photo/upload?project_id={pid}", {"file": jpeg()}, format="multipart")
    assert api.post(f"/api/structure/detect?project_id={pid}").json()["components"] == []
    saved = api.post(f"/api/structure/save?project_id={pid}",
                     {"components": [PARTS[0]]}, format="json").json()
    assert saved["components"][0]["source"] == "user"


@pytest.mark.django_db
def test_catalog_and_locations(api):
    assert len(api.get("/api/catalog").json()["materials"]) >= 10
    assert api.get("/api/locations").json()["states"][0]["cities"]
