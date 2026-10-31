from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from core import ai
from core.errors import AppError
from core.managers import photos, projects, structure


def image_file(size=(1000, 800), noisy=True, name="house.jpg"):
    img = Image.effect_noise(size, 64).convert("RGB") if noisy else Image.new("RGB", size, (128, 128, 128))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


GOOD = {"is_house_exterior": True, "facade_visible": True, "issues": [], "tips": []}


def test_local_quality_flags_small_and_flat():
    small = Image.effect_noise((400, 300), 64).convert("RGB")
    flat = Image.new("RGB", (1000, 800), (128, 128, 128))
    assert any("too small" in i for i in photos.local_quality(small))
    assert any("blurry" in i for i in photos.local_quality(flat))
    assert photos.local_quality(Image.effect_noise((1000, 800), 64).convert("RGB")) == []


@pytest.mark.django_db
def test_good_upload_becomes_primary(monkeypatch):
    monkeypatch.setattr(ai, "check_photo", lambda b, m: GOOD)
    project = projects.create("Test")
    photo = photos.upload(project, image_file())
    project.refresh_from_db()
    assert photo.quality_ok
    assert project.primary_photo_id == photo.id


@pytest.mark.django_db
def test_flat_upload_rejected_without_ai_call(monkeypatch):
    monkeypatch.setattr(ai, "check_photo", lambda b, m: pytest.fail("AI should not run"))
    project = projects.create("Test")
    photo = photos.upload(project, image_file(noisy=False))
    assert not photo.quality_ok
    assert photo.quality_report["tips"]


@pytest.mark.django_db
def test_not_a_house_rejected(monkeypatch):
    monkeypatch.setattr(ai, "check_photo", lambda b, m: {**GOOD, "is_house_exterior": False, "issues": ["This is a cat"]})
    project = projects.create("Test")
    assert not photos.upload(project, image_file()).quality_ok


@pytest.mark.django_db
def test_garbage_file_rejected():
    project = projects.create("Test")
    with pytest.raises(AppError) as err:
        photos.upload(project, SimpleUploadedFile("x.jpg", b"not an image"))
    assert err.value.code == "INVALID_IMAGE"


@pytest.mark.django_db
def test_detect_save_and_scale(monkeypatch):
    monkeypatch.setattr(ai, "check_photo", lambda b, m: GOOD)
    monkeypatch.setattr(ai, "detect_structure", lambda b, m, w, h: [
        {"type": "wall", "quad": [[0, 0], [1000, 0], [1000, 800], [0, 800]], "floor": 0, "confidence": 0.9},
        {"type": "door", "quad": [[100, 520], [160, 520], [160, 800], [100, 800]], "floor": 0, "confidence": 0.8},
    ])
    project = projects.create("Test")
    photos.upload(project, image_file())
    project.refresh_from_db()

    found = structure.detect(project)
    assert [c["type"] for c in found] == ["wall", "door"]
    project.refresh_from_db()
    assert project.px_per_ft == pytest.approx(40)  # 280 px door / 7 ft

    door = found[1]
    edited = structure.save(project, [
        {"id": door["id"], "type": "door", "quad": door["quad"], "floor": 0},
        {"type": "pillar", "quad": [[10, 10], [30, 10], [30, 700], [10, 700]], "floor": 0},
    ])
    assert sorted(c["type"] for c in edited) == ["door", "pillar"]  # wall removed
    assert next(c for c in edited if c["type"] == "pillar")["source"] == "user"

    project = structure.set_scale(project, component_id=door["id"], real_height_ft=8)
    assert project.px_per_ft == pytest.approx(35)
    assert project.scale_source == "user"


@pytest.mark.django_db
def test_save_rejects_bad_type(monkeypatch):
    monkeypatch.setattr(ai, "check_photo", lambda b, m: GOOD)
    project = projects.create("Test")
    photos.upload(project, image_file())
    project.refresh_from_db()
    with pytest.raises(AppError):
        structure.save(project, [{"type": "spaceship", "quad": [[0, 0], [1, 0], [1, 1], [0, 1]]}])


@pytest.mark.django_db
def test_get_project_errors():
    with pytest.raises(AppError) as bad:
        projects.get_project("not-a-uuid")
    assert bad.value.status == 400
    with pytest.raises(AppError) as missing:
        projects.get_project("00000000-0000-0000-0000-000000000000")
    assert missing.value.status == 404
