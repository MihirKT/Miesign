import pytest
from django.core.files.base import ContentFile

from core import ai
from core.catalog import load_catalog
from core.errors import AppError
from core.managers import designs, projects
from core.models import Component, Photo, Project

WALL_QUAD = [[0, 0], [100, 0], [100, 100], [0, 100]]


def components():
    return [{"id": "c1", "type": "wall", "quad": WALL_QUAD}, {"id": "c2", "type": "railing", "quad": WALL_QUAD}]


def test_validate_spec_drops_bad_assignments():
    spec = {"style": "modern", "palette": ["#AABBCC", "red"], "assignments": [
        {"target": "type:wall", "material_id": "texture_paint", "color": "#D9D4CC", "finish": "sand"},
        {"target": "type:wall", "material_id": "marble"},
        {"target": "type:balcony", "material_id": "glass_railing"},
        {"target": "type:railing", "material_id": "texture_paint"},
        {"target": "component:c2", "material_id": "glass_railing", "color": "bad"},
    ], "keep_unchanged": ["window", "nonsense"]}
    clean, warnings = designs.validate_spec(spec, load_catalog(), components())
    assert [a["material_id"] for a in clean["assignments"]] == ["texture_paint", "glass_railing"]
    assert clean["assignments"][1]["color"] is None
    assert clean["palette"] == ["#AABBCC"]
    assert clean["keep_unchanged"] == ["window"]
    assert len(warnings) == 3


def test_validate_spec_rejects_non_dict():
    with pytest.raises(AppError):
        designs.validate_spec("nope", load_catalog(), components())


def test_shortlist_respects_climate_maintenance_budget():
    items = designs.shortlist({"budget": "low", "climate": "coastal", "maintenance": "low"}, load_catalog())
    ids = {i["id"] for i in items}
    assert "brick_cladding_tiles" not in ids  # not coastal
    assert "ms_railing" not in ids  # high maintenance
    assert all(i["budget"] != "high" for i in items)


def test_validate_answers():
    with pytest.raises(AppError):
        designs.validate_answers({"budget": "infinite"})
    ok = designs.validate_answers({"budget": "low", "climate": "coastal", "style": "modern", "maintenance": "low"})
    assert ok["keep_unchanged"] == []


@pytest.fixture
def project_with_parts(db):
    project = projects.create("Test")
    photo = Photo(project_id=project.id, width=100, height=100, quality_ok=True)
    photo.file.save("p.jpg", ContentFile(b"jpg"))
    project.primary_photo_id = photo.id
    project.save()
    Component.objects.create(project_id=project.id, photo_id=photo.id, type="wall", quad=WALL_QUAD)
    return project


def test_from_text_saves_validated_design(project_with_parts, monkeypatch):
    monkeypatch.setattr(ai, "parse_text", lambda text, types, catalog: {
        "style": "modern", "assignments": [{"target": "type:wall", "material_id": "texture_paint"}],
        "notes": ["Marble mapped to slate"],
    })
    design = designs.from_text(project_with_parts, "grey texture walls")
    assert design.mode == "free_text"
    assert design.spec["assignments"][0]["material_id"] == "texture_paint"
    assert design.warnings == ["Marble mapped to slate"]


def test_render_cache_and_cap(project_with_parts, monkeypatch, settings):
    settings.RENDER_CAP = 2
    calls = []
    monkeypatch.setattr(ai, "render", lambda b, m, p: calls.append(p) or b"\x89PNG")
    design = designs.save(project_with_parts, None, "A", {"assignments": [
        {"target": "type:wall", "material_id": "texture_paint"}]})

    designs.render(design)
    designs.render(design)  # same spec -> cached
    assert len(calls) == 1

    design = designs.save(project_with_parts, design.id, "A", {"assignments": [
        {"target": "type:wall", "material_id": "exterior_emulsion"}]})
    designs.render(design)
    assert len(calls) == 2

    design = designs.save(project_with_parts, design.id, "A", {"assignments": []})
    with pytest.raises(AppError) as err:
        designs.render(design)
    assert err.value.status == 429
    assert Project.objects.get(id=project_with_parts.id).render_count == 2


def test_failed_render_refunds_cap(project_with_parts, monkeypatch):
    def boom(*a):
        raise ai.AiUnavailable()

    monkeypatch.setattr(ai, "render", boom)
    design = designs.save(project_with_parts, None, "A", {"assignments": []})
    with pytest.raises(ai.AiUnavailable):
        designs.render(design)
    assert Project.objects.get(id=project_with_parts.id).render_count == 0
