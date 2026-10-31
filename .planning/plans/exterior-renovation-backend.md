# Exterior Renovation — Backend Implementation Plan (1 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Django REST API that takes a house photo, detects its exterior parts with Gemini, turns free-text / guided answers / manual picks into a validated `DesignSpec`, renders the redesign, and returns a deterministic INR estimate + PDF using city-specific rates.

**Architecture:** `views.py` (thin HTTP) → `managers/*.py` (business logic, ORM writes) → `models.py` (SQLite) · `ai.py` (Vertex Gemini only, no DB) · `estimation.py` (pure math, no IO). The LLM never does arithmetic; all areas, quantities and money are plain Python.

**Tech Stack:** Python 3.12 · Django 5.2 · Django REST Framework · django-cors-headers · google-genai (Vertex AI) · Pillow · ReportLab · pytest + pytest-django.

**Sibling plans:** 2 — frontend (`exterior-renovation-frontend.md`, written after Task 12 freezes the API) · 3 — deploy + docs (`exterior-renovation-deploy.md`).

## Global Constraints

- Vertex project `project-1a771a61-0f54-4d61-b3b`, location `global`.
- Models: text/vision `gemini-3.5-flash`; image `gemini-3.1-flash-image`.
- JSON over the wire is `snake_case`; IDs are UUIDs passed as query params; mutations are `POST`.
- Error body: `{"error": {"code", "message", "status", "details"}}`.
- Every table: `id` UUID, `created_at`, `updated_at`, `deleted_at` (soft delete); no FK constraints.
- Timestamps UTC (`USE_TZ = True`).
- Currency INR; PDF prints `Rs` (ReportLab base fonts have no ₹ glyph) with Indian digit grouping.
- Render cap 8 per project; rate cache 30 days; rate sanity bounds 0.3×–3× base; tier multipliers T1 1.2 · T2 1.0 · T3 0.85.
- Photo minimum short side 800 px; stored photos are EXIF-rotated JPEG, long side ≤ 2048 px.
- Commit trailer on every commit: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

All commands run from `C:\Users\mihir\Desktop\E2M\backend` unless stated. Use Git Bash.

---

## File map

| File | Responsibility |
|---|---|
| `backend/requirements.txt` | pinned deps |
| `backend/manage.py`, `backend/config/{__init__,settings,urls,wsgi}.py` | Django project |
| `backend/pytest.ini`, `backend/conftest.py` | test config, tmp media |
| `backend/core/{__init__,apps}.py` | app |
| `backend/core/models.py` | 6 models + soft delete base |
| `backend/core/errors.py` | `AppError` + DRF exception handler |
| `backend/core/catalog.py` | load `catalog.json` / `cities.json`, `city_tier` |
| `backend/core/data/catalog.json`, `cities.json` | seed data |
| `backend/core/estimation.py` | geometry, scale, quantities, estimate |
| `backend/core/ai.py` | Gemini calls + pure helpers |
| `backend/core/managers/{__init__,projects,photos,structure,rates,designs,estimates,report}.py` | business logic |
| `backend/core/serializers.py` | model → dict |
| `backend/core/views.py`, `backend/core/urls.py` | HTTP |
| `backend/core/tests/test_*.py` | tests |
| `backend/scripts/smoke_ai.py` | live Vertex smoke run |

---

### Task 1: Scaffold Django project + git

**Files:**
- Create: `.gitignore`, `backend/requirements.txt`, `backend/manage.py`, `backend/config/__init__.py`, `backend/config/settings.py`, `backend/config/urls.py`, `backend/config/wsgi.py`, `backend/core/__init__.py`, `backend/core/apps.py`, `backend/core/tests/__init__.py`, `backend/pytest.ini`, `backend/conftest.py`
- Test: `backend/core/tests/test_smoke.py`

**Interfaces:**
- Produces: settings names `GCP_PROJECT`, `GCP_LOCATION`, `MODEL_TEXT`, `MODEL_IMAGE`, `RENDER_CAP`, `RATE_CACHE_DAYS`, `MIN_PHOTO_SIDE`, `BLUR_MIN_VARIANCE`, `MAX_PHOTOS`; DRF exception handler path `core.errors.exception_handler` (created in Task 2).

- [ ] **Step 1: git init + ignore**

Run from `C:\Users\mihir\Desktop\E2M`:
```bash
git init -b main
```

`.gitignore`:
```gitignore
__pycache__/
*.pyc
.venv/
backend/db.sqlite3
backend/media/
node_modules/
frontend/dist/
.env
```

- [ ] **Step 2: venv + deps**

`backend/requirements.txt`:
```text
Django>=5.2,<6
djangorestframework>=3.15,<4
django-cors-headers>=4.4,<5
google-genai>=1.20,<2
Pillow>=11,<12
reportlab>=4.2,<5
gunicorn>=23,<24
pytest>=8,<9
pytest-django>=4.9,<5
```

Run:
```bash
python -m venv .venv && source .venv/Scripts/activate && pip install -r requirements.txt
```
Expected: `Successfully installed ...` (no errors).

- [ ] **Step 3: Django files**

`backend/manage.py`:
```python
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
```

`backend/config/__init__.py`: empty file.

`backend/config/settings.py`:
```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-not-secret")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = []

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DATA_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024

CORS_ALLOWED_ORIGINS = [o for o in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o]

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "core.errors.exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
}

GCP_PROJECT = os.environ.get("GCP_PROJECT", "project-1a771a61-0f54-4d61-b3b")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "global")
MODEL_TEXT = os.environ.get("MODEL_TEXT", "gemini-3.5-flash")
MODEL_IMAGE = os.environ.get("MODEL_IMAGE", "gemini-3.1-flash-image")

RENDER_CAP = int(os.environ.get("RENDER_CAP", "8"))
RATE_CACHE_DAYS = int(os.environ.get("RATE_CACHE_DAYS", "30"))
MIN_PHOTO_SIDE = int(os.environ.get("MIN_PHOTO_SIDE", "800"))
# Variance of Pillow FIND_EDGES on a 512px greyscale thumbnail; tuned in Task 13.
BLUR_MIN_VARIANCE = float(os.environ.get("BLUR_MIN_VARIANCE", "40"))
MAX_PHOTOS = int(os.environ.get("MAX_PHOTOS", "5"))
```

`backend/config/urls.py`:
```python
from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("api/", include("core.urls")),
    # ponytail: Django serves media directly; move to a bucket/CDN if traffic grows.
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
```

`backend/config/wsgi.py`:
```python
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
```

`backend/core/__init__.py`: empty file. `backend/core/tests/__init__.py`: empty file.

`backend/core/apps.py`:
```python
from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"
    default_auto_field = "django.db.models.BigAutoField"
```

`backend/core/urls.py` (temporary, replaced in Task 12):
```python
urlpatterns = []
```

`backend/core/errors.py` (temporary stub so settings resolve; full version in Task 2):
```python
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    return drf_exception_handler(exc, context)
```

`backend/pytest.ini`:
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = test_*.py
addopts = -q
```

`backend/conftest.py`:
```python
import pytest


@pytest.fixture(autouse=True)
def tmp_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
```

- [ ] **Step 4: Write smoke test**

`backend/core/tests/test_smoke.py`:
```python
from django.conf import settings


def test_settings_load():
    assert settings.MODEL_TEXT == "gemini-3.5-flash"
    assert settings.RENDER_CAP == 8
```

- [ ] **Step 5: Run**

Run: `python manage.py check && pytest`
Expected: `System check identified no issues (0 silenced).` then `1 passed`.

- [ ] **Step 6: Commit**

```bash
cd .. && git add .gitignore backend && git commit -m "chore: scaffold Django backend

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Errors + models

**Files:**
- Modify: `backend/core/errors.py` (replace stub)
- Create: `backend/core/models.py`, `backend/core/migrations/0001_initial.py` (generated)
- Test: `backend/core/tests/test_models.py`

**Interfaces:**
- Produces: `AppError(code: str, message: str, status: int = 400, details: list | None = None)`; models `Project, Photo, Component, Design, RateCache, RateOverride` with `.objects` (active only), `.all_objects`, `.soft_delete()`.
- Field names (used by every later task):
  - `Project`: `name, state, city, px_per_ft (float|None), scale_source ('default'|'user'), primary_photo_id (UUID|None), render_count`
  - `Photo`: `project_id, file, mime, width, height, quality_ok, quality_report (dict: issues[], tips[])`
  - `Component`: `project_id, photo_id, type, quad ([[x,y]×4]), floor, source ('ai'|'user'), confidence (float|None)`
  - `Design`: `project_id, name, mode ('free_text'|'guided'|'manual'), input (dict), spec (dict), rationale, warnings (list), render_file, render_spec_hash`
  - `RateCache`: `state, city, material_id, material_rate, labor_rate, source ('web'|'estimated'), sources (list), fetched_at`
  - `RateOverride`: `project_id, material_id, material_rate (float|None), labor_rate (float|None)`

- [ ] **Step 1: Write the failing test**

`backend/core/tests/test_models.py`:
```python
import pytest

from core.models import Project


@pytest.mark.django_db
def test_soft_delete_hides_from_default_manager():
    project = Project.objects.create(name="Test")
    project.soft_delete()

    assert Project.objects.filter(id=project.id).count() == 0
    assert Project.all_objects.get(id=project.id).deleted_at is not None


@pytest.mark.django_db
def test_project_defaults():
    project = Project.objects.create()
    assert project.scale_source == "default"
    assert project.render_count == 0
    assert project.px_per_ft is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest core/tests/test_models.py`
Expected: FAIL — `ImportError: cannot import name 'Project'`.

- [ ] **Step 3: Implement**

`backend/core/errors.py`:
```python
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class AppError(Exception):
    def __init__(self, code, message, status=400, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or []


def _body(code, message, status, details):
    return {"error": {"code": code, "message": message, "status": status, "details": details}}


def exception_handler(exc, context):
    if isinstance(exc, AppError):
        return Response(_body(exc.code, exc.message, exc.status, exc.details), status=exc.status)
    response = drf_exception_handler(exc, context)
    if response is not None:
        detail = response.data.get("detail") if isinstance(response.data, dict) else None
        response.data = _body(
            "NOT_FOUND" if response.status_code == 404 else "BAD_REQUEST",
            str(detail or "Request could not be processed."),
            response.status_code,
            [] if detail else response.data,
        )
    return response
```

`backend/core/models.py`:
```python
import uuid

from django.db import models
from django.utils import timezone


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Base(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])


class Project(Base):
    name = models.TextField(default="My house")
    state = models.TextField(blank=True, default="")
    city = models.TextField(blank=True, default="")
    px_per_ft = models.FloatField(null=True, blank=True)
    scale_source = models.TextField(default="default")
    primary_photo_id = models.UUIDField(null=True, blank=True)
    render_count = models.IntegerField(default=0)


class Photo(Base):
    project_id = models.UUIDField(db_index=True)
    file = models.FileField(upload_to="photos/")
    mime = models.TextField(default="image/jpeg")
    width = models.IntegerField()
    height = models.IntegerField()
    quality_ok = models.BooleanField(default=False)
    quality_report = models.JSONField(default=dict)


class Component(Base):
    project_id = models.UUIDField(db_index=True)
    photo_id = models.UUIDField(db_index=True)
    type = models.TextField()
    quad = models.JSONField()
    floor = models.IntegerField(default=0)
    source = models.TextField(default="ai")
    confidence = models.FloatField(null=True, blank=True)


class Design(Base):
    project_id = models.UUIDField(db_index=True)
    name = models.TextField()
    mode = models.TextField()
    input = models.JSONField(default=dict)
    spec = models.JSONField(default=dict)
    rationale = models.TextField(blank=True, default="")
    warnings = models.JSONField(default=list)
    render_file = models.FileField(upload_to="renders/", null=True, blank=True)
    render_spec_hash = models.TextField(blank=True, default="")


class RateCache(Base):
    state = models.TextField()
    city = models.TextField()
    material_id = models.TextField()
    material_rate = models.FloatField()
    labor_rate = models.FloatField()
    source = models.TextField()
    sources = models.JSONField(default=list)
    fetched_at = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["state", "city", "material_id"], name="uniq_rate_city_material")]


class RateOverride(Base):
    project_id = models.UUIDField(db_index=True)
    material_id = models.TextField()
    material_rate = models.FloatField(null=True, blank=True)
    labor_rate = models.FloatField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["project_id", "material_id"], name="uniq_override_project_material")]
```

Run: `python manage.py makemigrations core`
Expected: `Migrations for 'core': core/migrations/0001_initial.py`.

- [ ] **Step 4: Run tests**

Run: `pytest core/tests/test_models.py`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
cd .. && git add backend/core && git commit -m "feat: add models with soft delete and API error handler

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Seed data + catalog loader

**Files:**
- Create: `backend/core/data/catalog.json`, `backend/core/data/cities.json`, `backend/core/catalog.py`
- Test: `backend/core/tests/test_catalog.py`

**Interfaces:**
- Produces: `load_catalog() -> dict[str, dict]` keyed by `id`; item keys `id, name, category, applies_to: list[str], rate_unit: 'sqft'|'rft', qty_unit: 'L'|'kg'|'pcs'|'sqft'|'rft', coats?, coverage_per_unit?, piece_sqft?, wastage_pct, base_material_rate, base_labor_rate, durability_years, maintenance: 'low'|'medium'|'high', budget: 'low'|'mid'|'high', climates: list[str], styles: list[str], render_hint`.
- `load_cities() -> list[{"name": state, "cities": [{"name", "tier"}]}]`; `city_tier(state: str, city: str) -> int` (unknown → 2).

- [ ] **Step 1: Write the failing test**

`backend/core/tests/test_catalog.py`:
```python
from core.catalog import city_tier, load_catalog, load_cities
from core.estimation import COMPONENT_TYPES

REQUIRED = {
    "id", "name", "category", "applies_to", "rate_unit", "qty_unit", "wastage_pct",
    "base_material_rate", "base_labor_rate", "durability_years", "maintenance",
    "budget", "climates", "styles", "render_hint",
}


def test_catalog_items_are_complete():
    catalog = load_catalog()
    assert len(catalog) >= 10
    for item_id, item in catalog.items():
        assert REQUIRED <= item.keys(), item_id
        assert set(item["applies_to"]) <= set(COMPONENT_TYPES), item_id
        assert item["rate_unit"] in {"sqft", "rft"}
        if item["qty_unit"] in {"L", "kg"}:
            assert item["coverage_per_unit"] > 0 and item["coats"] >= 1
        if item["qty_unit"] == "pcs":
            assert item["piece_sqft"] > 0


def test_cities_have_tiers():
    states = load_cities()
    assert sum(len(s["cities"]) for s in states) >= 80
    assert city_tier("Maharashtra", "Mumbai") == 1
    assert city_tier("Kerala", "Thrissur") == 3
    assert city_tier("Nowhere", "Unknown") == 2
```

Note: this test imports `COMPONENT_TYPES` from `core.estimation`; create that module's first line now so the import works:

`backend/core/estimation.py` (Task 4 extends it):
```python
COMPONENT_TYPES = ["wall", "window", "door", "balcony", "pillar", "parapet", "gate", "roof_edge", "railing"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest core/tests/test_catalog.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.catalog'`.

- [ ] **Step 3: Implement**

`backend/core/data/catalog.json` (base rates are reference INR values for a Tier-2 city; documented as such):
```json
[
  {"id": "exterior_emulsion", "name": "Exterior emulsion paint", "category": "Paint",
   "applies_to": ["wall", "parapet", "balcony", "pillar", "roof_edge", "gate"],
   "rate_unit": "sqft", "qty_unit": "L", "coats": 2, "coverage_per_unit": 110, "wastage_pct": 5,
   "base_material_rate": 16, "base_labor_rate": 10, "durability_years": "5-7", "maintenance": "medium",
   "budget": "low", "climates": ["hot_dry", "moderate", "heavy_rain"], "styles": ["modern", "traditional", "minimal"],
   "render_hint": "smooth matte weatherproof exterior emulsion paint"},
  {"id": "elastomeric_paint", "name": "Elastomeric waterproof paint", "category": "Paint",
   "applies_to": ["wall", "parapet", "balcony", "pillar", "roof_edge"],
   "rate_unit": "sqft", "qty_unit": "L", "coats": 2, "coverage_per_unit": 90, "wastage_pct": 5,
   "base_material_rate": 28, "base_labor_rate": 12, "durability_years": "8-10", "maintenance": "low",
   "budget": "mid", "climates": ["coastal", "heavy_rain", "moderate", "hot_dry"], "styles": ["modern", "traditional", "minimal"],
   "render_hint": "low-sheen elastomeric waterproof exterior paint"},
  {"id": "texture_paint", "name": "Texture finish (sand / roller)", "category": "Texture finish",
   "applies_to": ["wall", "parapet", "pillar", "balcony"],
   "rate_unit": "sqft", "qty_unit": "kg", "coats": 1, "coverage_per_unit": 10, "wastage_pct": 8,
   "base_material_rate": 35, "base_labor_rate": 22, "durability_years": "8-10", "maintenance": "low",
   "budget": "mid", "climates": ["hot_dry", "moderate", "heavy_rain"], "styles": ["modern", "luxe", "traditional"],
   "render_hint": "fine sand-grain textured exterior wall finish"},
  {"id": "stone_cladding_natural", "name": "Natural stone cladding (sandstone)", "category": "Stone cladding",
   "applies_to": ["wall", "pillar", "parapet", "gate"],
   "rate_unit": "sqft", "qty_unit": "sqft", "wastage_pct": 10,
   "base_material_rate": 120, "base_labor_rate": 60, "durability_years": "25+", "maintenance": "low",
   "budget": "high", "climates": ["hot_dry", "moderate", "heavy_rain", "coastal"], "styles": ["traditional", "luxe"],
   "render_hint": "beige sandstone split-face stone cladding with natural joints"},
  {"id": "stone_cladding_slate", "name": "Slate stone cladding", "category": "Stone cladding",
   "applies_to": ["wall", "pillar", "parapet", "gate"],
   "rate_unit": "sqft", "qty_unit": "sqft", "wastage_pct": 10,
   "base_material_rate": 90, "base_labor_rate": 55, "durability_years": "25+", "maintenance": "low",
   "budget": "mid", "climates": ["hot_dry", "moderate", "heavy_rain", "coastal"], "styles": ["modern", "luxe", "minimal"],
   "render_hint": "dark grey slate ledge-stone cladding panels"},
  {"id": "vitrified_wall_tiles", "name": "Vitrified elevation tiles (2 x 1 ft)", "category": "Tiles",
   "applies_to": ["wall", "pillar", "parapet", "balcony"],
   "rate_unit": "sqft", "qty_unit": "pcs", "piece_sqft": 2, "wastage_pct": 10,
   "base_material_rate": 70, "base_labor_rate": 40, "durability_years": "15-20", "maintenance": "low",
   "budget": "mid", "climates": ["coastal", "heavy_rain", "moderate", "hot_dry"], "styles": ["modern", "minimal"],
   "render_hint": "large-format matte vitrified elevation tiles with thin grout lines"},
  {"id": "brick_cladding_tiles", "name": "Brick cladding tiles", "category": "Tiles",
   "applies_to": ["wall", "pillar", "parapet", "gate"],
   "rate_unit": "sqft", "qty_unit": "pcs", "piece_sqft": 0.1875, "wastage_pct": 12,
   "base_material_rate": 85, "base_labor_rate": 45, "durability_years": "20+", "maintenance": "low",
   "budget": "mid", "climates": ["hot_dry", "moderate"], "styles": ["traditional", "modern"],
   "render_hint": "terracotta exposed-brick cladding tiles"},
  {"id": "acp_panel", "name": "ACP panels (4 mm)", "category": "Panels",
   "applies_to": ["wall", "parapet", "balcony", "roof_edge"],
   "rate_unit": "sqft", "qty_unit": "sqft", "wastage_pct": 8,
   "base_material_rate": 180, "base_labor_rate": 70, "durability_years": "15-20", "maintenance": "low",
   "budget": "high", "climates": ["hot_dry", "moderate", "heavy_rain"], "styles": ["modern", "minimal"],
   "render_hint": "flat aluminium composite panels with crisp reveal joints"},
  {"id": "wpc_wood_panel", "name": "WPC wood-look louvers", "category": "Panels",
   "applies_to": ["wall", "balcony", "parapet", "gate"],
   "rate_unit": "sqft", "qty_unit": "sqft", "wastage_pct": 8,
   "base_material_rate": 260, "base_labor_rate": 80, "durability_years": "15-20", "maintenance": "low",
   "budget": "high", "climates": ["moderate", "hot_dry", "heavy_rain", "coastal"], "styles": ["modern", "luxe"],
   "render_hint": "warm teak-tone WPC vertical wooden louvers"},
  {"id": "glass_railing", "name": "Toughened glass railing", "category": "Railing",
   "applies_to": ["railing", "balcony", "parapet"],
   "rate_unit": "rft", "qty_unit": "rft", "wastage_pct": 5,
   "base_material_rate": 1800, "base_labor_rate": 400, "durability_years": "20+", "maintenance": "medium",
   "budget": "high", "climates": ["moderate", "hot_dry", "heavy_rain", "coastal"], "styles": ["modern", "minimal", "luxe"],
   "render_hint": "frameless 12 mm toughened glass railing with steel spigots"},
  {"id": "ss_railing", "name": "Stainless steel railing (SS 304)", "category": "Railing",
   "applies_to": ["railing", "balcony", "parapet"],
   "rate_unit": "rft", "qty_unit": "rft", "wastage_pct": 5,
   "base_material_rate": 1100, "base_labor_rate": 300, "durability_years": "20+", "maintenance": "low",
   "budget": "mid", "climates": ["coastal", "heavy_rain", "moderate", "hot_dry"], "styles": ["modern", "minimal"],
   "render_hint": "brushed stainless steel railing with horizontal rods"},
  {"id": "ms_railing", "name": "Mild steel railing (painted)", "category": "Railing",
   "applies_to": ["railing", "balcony", "parapet", "gate"],
   "rate_unit": "rft", "qty_unit": "rft", "wastage_pct": 5,
   "base_material_rate": 550, "base_labor_rate": 200, "durability_years": "8-12", "maintenance": "high",
   "budget": "low", "climates": ["hot_dry", "moderate"], "styles": ["traditional", "minimal"],
   "render_hint": "painted mild steel railing with simple vertical bars"}
]
```

`backend/core/data/cities.json`:
```json
[
  {"name": "Andhra Pradesh", "cities": [{"name": "Visakhapatnam", "tier": 2}, {"name": "Vijayawada", "tier": 2}, {"name": "Guntur", "tier": 3}, {"name": "Tirupati", "tier": 3}, {"name": "Nellore", "tier": 3}]},
  {"name": "Assam", "cities": [{"name": "Guwahati", "tier": 2}, {"name": "Silchar", "tier": 3}, {"name": "Dibrugarh", "tier": 3}]},
  {"name": "Bihar", "cities": [{"name": "Patna", "tier": 2}, {"name": "Gaya", "tier": 3}, {"name": "Bhagalpur", "tier": 3}, {"name": "Muzaffarpur", "tier": 3}]},
  {"name": "Chandigarh", "cities": [{"name": "Chandigarh", "tier": 2}]},
  {"name": "Chhattisgarh", "cities": [{"name": "Raipur", "tier": 2}, {"name": "Bhilai", "tier": 3}, {"name": "Bilaspur", "tier": 3}]},
  {"name": "Delhi", "cities": [{"name": "New Delhi", "tier": 1}]},
  {"name": "Goa", "cities": [{"name": "Panaji", "tier": 3}, {"name": "Margao", "tier": 3}]},
  {"name": "Gujarat", "cities": [{"name": "Ahmedabad", "tier": 1}, {"name": "Surat", "tier": 2}, {"name": "Vadodara", "tier": 2}, {"name": "Rajkot", "tier": 2}, {"name": "Gandhinagar", "tier": 3}, {"name": "Bhavnagar", "tier": 3}]},
  {"name": "Haryana", "cities": [{"name": "Gurugram", "tier": 1}, {"name": "Faridabad", "tier": 2}, {"name": "Panipat", "tier": 3}, {"name": "Ambala", "tier": 3}]},
  {"name": "Himachal Pradesh", "cities": [{"name": "Shimla", "tier": 3}, {"name": "Dharamshala", "tier": 3}]},
  {"name": "Jammu and Kashmir", "cities": [{"name": "Jammu", "tier": 3}, {"name": "Srinagar", "tier": 3}]},
  {"name": "Jharkhand", "cities": [{"name": "Ranchi", "tier": 2}, {"name": "Jamshedpur", "tier": 2}, {"name": "Dhanbad", "tier": 3}]},
  {"name": "Karnataka", "cities": [{"name": "Bengaluru", "tier": 1}, {"name": "Mysuru", "tier": 2}, {"name": "Mangaluru", "tier": 2}, {"name": "Hubballi", "tier": 3}, {"name": "Belagavi", "tier": 3}]},
  {"name": "Kerala", "cities": [{"name": "Kochi", "tier": 2}, {"name": "Thiruvananthapuram", "tier": 2}, {"name": "Kozhikode", "tier": 2}, {"name": "Thrissur", "tier": 3}]},
  {"name": "Madhya Pradesh", "cities": [{"name": "Indore", "tier": 2}, {"name": "Bhopal", "tier": 2}, {"name": "Jabalpur", "tier": 3}, {"name": "Gwalior", "tier": 3}]},
  {"name": "Maharashtra", "cities": [{"name": "Mumbai", "tier": 1}, {"name": "Pune", "tier": 1}, {"name": "Thane", "tier": 1}, {"name": "Navi Mumbai", "tier": 1}, {"name": "Nagpur", "tier": 2}, {"name": "Nashik", "tier": 2}, {"name": "Aurangabad", "tier": 2}, {"name": "Kolhapur", "tier": 3}, {"name": "Solapur", "tier": 3}]},
  {"name": "Odisha", "cities": [{"name": "Bhubaneswar", "tier": 2}, {"name": "Cuttack", "tier": 3}, {"name": "Rourkela", "tier": 3}]},
  {"name": "Punjab", "cities": [{"name": "Ludhiana", "tier": 2}, {"name": "Amritsar", "tier": 2}, {"name": "Mohali", "tier": 2}, {"name": "Jalandhar", "tier": 3}]},
  {"name": "Rajasthan", "cities": [{"name": "Jaipur", "tier": 2}, {"name": "Jodhpur", "tier": 2}, {"name": "Udaipur", "tier": 3}, {"name": "Kota", "tier": 3}, {"name": "Ajmer", "tier": 3}]},
  {"name": "Tamil Nadu", "cities": [{"name": "Chennai", "tier": 1}, {"name": "Coimbatore", "tier": 2}, {"name": "Madurai", "tier": 2}, {"name": "Tiruchirappalli", "tier": 3}, {"name": "Salem", "tier": 3}]},
  {"name": "Telangana", "cities": [{"name": "Hyderabad", "tier": 1}, {"name": "Warangal", "tier": 3}]},
  {"name": "Uttar Pradesh", "cities": [{"name": "Noida", "tier": 1}, {"name": "Lucknow", "tier": 2}, {"name": "Kanpur", "tier": 2}, {"name": "Ghaziabad", "tier": 2}, {"name": "Agra", "tier": 2}, {"name": "Varanasi", "tier": 2}, {"name": "Prayagraj", "tier": 3}, {"name": "Meerut", "tier": 3}]},
  {"name": "Uttarakhand", "cities": [{"name": "Dehradun", "tier": 2}, {"name": "Haridwar", "tier": 3}]},
  {"name": "West Bengal", "cities": [{"name": "Kolkata", "tier": 1}, {"name": "Howrah", "tier": 2}, {"name": "Siliguri", "tier": 3}, {"name": "Durgapur", "tier": 3}]}
]
```

That is 91 cities.

`backend/core/catalog.py`:
```python
import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_TIER = 2


@lru_cache(maxsize=1)
def load_catalog():
    items = json.loads((DATA_DIR / "catalog.json").read_text(encoding="utf-8"))
    return {item["id"]: item for item in items}


@lru_cache(maxsize=1)
def load_cities():
    return json.loads((DATA_DIR / "cities.json").read_text(encoding="utf-8"))


def city_tier(state, city):
    for entry in load_cities():
        if entry["name"] == state:
            for c in entry["cities"]:
                if c["name"] == city:
                    return c["tier"]
    return DEFAULT_TIER
```

- [ ] **Step 4: Run tests**

Run: `pytest core/tests/test_catalog.py`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
cd .. && git add backend/core && git commit -m "feat: add material catalog and city tiers

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Geometry + scale (pure)

**Files:**
- Modify: `backend/core/estimation.py`
- Test: `backend/core/tests/test_estimation.py`

**Interfaces:**
- Consumes: `COMPONENT_TYPES` (Task 3).
- Produces:
  - `polygon_area_px(quad) -> float`, `bbox(quad) -> (x0, y0, x1, y1)`, `width_px(quad)`, `height_px(quad)`, `centroid(quad) -> (x, y)`, `point_in_polygon(pt, poly) -> bool`
  - `area_sqft(quad, px_per_ft) -> float`
  - `scale_from_component(quad, real_height_ft) -> float` (raises `ValueError`)
  - `default_scale(components: list[dict], image_height: int) -> float`
  - `measure(component: dict, components: list[dict], px_per_ft: float, rate_unit: str) -> float`
  - `walls_overlap_warnings(components) -> list[str]`
  - component dict shape everywhere: `{"id": str, "type": str, "quad": [[x, y]×4], "floor": int, "source": str, "confidence": float|None}`

- [ ] **Step 1: Write the failing tests**

`backend/core/tests/test_estimation.py`:
```python
import pytest

from core.estimation import (
    area_sqft, default_scale, measure, point_in_polygon, polygon_area_px,
    scale_from_component, walls_overlap_warnings,
)


def rect(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def comp(cid, ctype, quad):
    return {"id": cid, "type": ctype, "quad": quad, "floor": 0, "source": "ai", "confidence": None}


def test_rect_area():
    assert polygon_area_px(rect(0, 0, 100, 50)) == 5000
    assert area_sqft(rect(0, 0, 100, 100), 10) == pytest.approx(100)


def test_degenerate_quad_is_zero():
    assert area_sqft([[5, 5], [5, 5], [5, 5], [5, 5]], 10) == 0
    assert area_sqft(rect(0, 0, 100, 100), 0) == 0


def test_point_in_polygon():
    square = rect(0, 0, 10, 10)
    assert point_in_polygon((5, 5), square)
    assert not point_in_polygon((15, 5), square)


def test_wall_net_subtracts_contained_openings_only():
    wall = comp("w", "wall", rect(0, 0, 100, 100))
    inside = comp("a", "window", rect(10, 10, 30, 30))
    outside = comp("b", "window", rect(200, 200, 220, 220))
    value = measure(wall, [wall, inside, outside], px_per_ft=10, rate_unit="sqft")
    assert value == pytest.approx(96)


def test_pillar_counts_four_faces():
    pillar = comp("p", "pillar", rect(0, 0, 10, 100))
    assert measure(pillar, [pillar], 10, "sqft") == pytest.approx(40)


def test_rft_uses_width():
    railing = comp("r", "railing", rect(0, 0, 50, 10))
    assert measure(railing, [railing], 10, "rft") == pytest.approx(5)


def test_scale_from_component():
    assert scale_from_component(rect(0, 0, 30, 140), 7) == pytest.approx(20)
    with pytest.raises(ValueError):
        scale_from_component(rect(0, 0, 30, 140), 0)


def test_default_scale_prefers_door_then_window_then_image():
    door = comp("d", "door", rect(0, 0, 30, 140))
    window = comp("w", "window", rect(0, 0, 40, 80))
    assert default_scale([door, window], 1000) == pytest.approx(20)
    assert default_scale([window], 1000) == pytest.approx(20)
    assert default_scale([], 1000) == pytest.approx(50)


def test_overlapping_walls_warn():
    a = comp("a", "wall", rect(0, 0, 100, 100))
    b = comp("b", "wall", rect(50, 0, 150, 100))
    c = comp("c", "wall", rect(300, 0, 400, 100))
    assert len(walls_overlap_warnings([a, b])) == 1
    assert walls_overlap_warnings([a, c]) == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest core/tests/test_estimation.py`
Expected: FAIL — `ImportError: cannot import name 'area_sqft'`.

- [ ] **Step 3: Implement**

Append to `backend/core/estimation.py` (keep the `COMPONENT_TYPES` line at the top):
```python
import math
from statistics import mean

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
```

Move the two `import` lines (`import math`, `from statistics import mean`) to the very top of the file, above `COMPONENT_TYPES`.

- [ ] **Step 4: Run tests**

Run: `pytest core/tests/test_estimation.py`
Expected: `9 passed`.

- [ ] **Step 5: Commit**

```bash
cd .. && git add backend/core && git commit -m "feat: add facade geometry and scale calibration

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Quantities + estimate (pure)

**Files:**
- Modify: `backend/core/estimation.py`
- Test: `backend/core/tests/test_estimate.py`

**Interfaces:**
- Consumes: Task 4 helpers.
- Produces:
  - `quantity(item: dict, measure_value: float) -> float | int`
  - `resolve_assignments(components, spec) -> list[tuple[component, assignment]]`
  - `estimate(components, spec, catalog, rates, px_per_ft, scale_source) -> dict` with keys `scale{px_per_ft, source}`, `lines[]`, `grand_total`, `assumptions[]`, `warnings[]`.
  - `rates` shape (from Task 8): `{material_id: {"material_rate", "labor_rate", "source", "sources", "fetched_at", "material_id", "rate_unit"}}`.
  - line keys: `category, material_id, name, targets (list[str]), measure, rate_unit, quantity, qty_unit, wastage_pct, material_rate, labor_rate, rate_source, material_cost, labor_cost, total`.
- Cost rule: `material_cost = round(measure × (1 + wastage) × material_rate)`, `labor_cost = round(measure × labor_rate)`.

- [ ] **Step 1: Write the failing tests**

`backend/core/tests/test_estimate.py`:
```python
from core.estimation import estimate, quantity, resolve_assignments

PAINT = {"id": "paint", "name": "Paint", "category": "Paint", "applies_to": ["wall", "pillar"],
         "rate_unit": "sqft", "qty_unit": "L", "coats": 2, "coverage_per_unit": 110, "wastage_pct": 5}
TILE = {"id": "tile", "name": "Tile", "category": "Tiles", "applies_to": ["wall"],
        "rate_unit": "sqft", "qty_unit": "pcs", "piece_sqft": 2, "wastage_pct": 10}
RAIL = {"id": "rail", "name": "Rail", "category": "Railing", "applies_to": ["railing"],
        "rate_unit": "rft", "qty_unit": "rft", "wastage_pct": 5}
CATALOG = {i["id"]: i for i in (PAINT, TILE, RAIL)}
RATES = {
    "paint": {"material_rate": 15, "labor_rate": 10, "source": "web"},
    "tile": {"material_rate": 70, "labor_rate": 40, "source": "estimated"},
    "rail": {"material_rate": 1000, "labor_rate": 200, "source": "override"},
}


def rect(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def comp(cid, ctype, quad):
    return {"id": cid, "type": ctype, "quad": quad, "floor": 0, "source": "ai", "confidence": None}


WALL = comp("w1", "wall", rect(0, 0, 100, 100))
WINDOW = comp("win", "window", rect(10, 10, 30, 30))
PILLAR = comp("p1", "pillar", rect(200, 0, 210, 100))
RAILING = comp("r1", "railing", rect(0, 200, 50, 210))
COMPONENTS = [WALL, WINDOW, PILLAR, RAILING]


def test_quantity_units():
    assert quantity(PAINT, 96) == 1.8
    assert quantity(TILE, 96) == 53
    assert quantity(RAIL, 5) == 5.2


def test_component_assignment_beats_type_assignment():
    spec = {"assignments": [
        {"target": "type:wall", "material_id": "paint"},
        {"target": "component:w1", "material_id": "tile"},
    ]}
    pairs = resolve_assignments(COMPONENTS, spec)
    assert [(c["id"], a["material_id"]) for c, a in pairs] == [("w1", "tile")]


def test_keep_unchanged_and_openings_are_skipped():
    spec = {"assignments": [{"target": "type:wall", "material_id": "paint"},
                            {"target": "type:window", "material_id": "paint"}],
            "keep_unchanged": ["wall"]}
    assert resolve_assignments(COMPONENTS, spec) == []


def test_estimate_lines_and_totals():
    spec = {"assignments": [
        {"target": "type:wall", "material_id": "paint"},
        {"target": "type:pillar", "material_id": "paint"},
        {"target": "type:railing", "material_id": "rail"},
    ]}
    result = estimate(COMPONENTS, spec, CATALOG, RATES, px_per_ft=10, scale_source="user")

    paint = next(line for line in result["lines"] if line["material_id"] == "paint")
    assert paint["measure"] == 136.0  # wall 96 + pillar 40
    assert paint["material_cost"] == round(136 * 1.05 * 15)
    assert paint["labor_cost"] == 1360
    assert sorted(paint["targets"]) == ["pillar×1", "wall×1"]

    rail = next(line for line in result["lines"] if line["material_id"] == "rail")
    assert rail["measure"] == 5.0
    assert rail["rate_source"] == "override"
    assert result["grand_total"] == sum(line["total"] for line in result["lines"])
    assert result["scale"] == {"px_per_ft": 10.0, "source": "user"}


def test_unsuitable_material_is_skipped_with_warning():
    spec = {"assignments": [{"target": "type:railing", "material_id": "tile"}]}
    result = estimate(COMPONENTS, spec, CATALOG, RATES, 10, "user")
    assert result["lines"] == []
    assert any("Tile" in w for w in result["warnings"])


def test_default_scale_is_flagged():
    result = estimate(COMPONENTS, {"assignments": []}, CATALOG, RATES, 10, "default")
    assert any("assumed" in a for a in result["assumptions"])
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest core/tests/test_estimate.py`
Expected: FAIL — `ImportError: cannot import name 'estimate'`.

- [ ] **Step 3: Implement**

Append to `backend/core/estimation.py`:
```python
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
```

- [ ] **Step 4: Run tests**

Run: `pytest core/tests/test_estimate.py core/tests/test_estimation.py`
Expected: `15 passed`.

- [ ] **Step 5: Commit**

```bash
cd .. && git add backend/core && git commit -m "feat: add quantity and cost estimation engine

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: AI service — pure helpers

**Files:**
- Create: `backend/core/ai.py`
- Test: `backend/core/tests/test_ai_helpers.py`

**Interfaces:**
- Consumes: `bbox` (Task 4), `AppError` (Task 2).
- Produces: `extract_json(text) -> dict|list` (raises `ValueError`), `box_to_quad(box_2d, width, height) -> [[x,y]×4]`, `build_render_prompt(spec, components, catalog, width, height) -> str`, `AiUnavailable(AppError)` (status 503).

- [ ] **Step 1: Write the failing tests**

`backend/core/tests/test_ai_helpers.py`:
```python
import json

import pytest

from core.ai import box_to_quad, build_render_prompt, extract_json

CATALOG = {"slate": {"id": "slate", "name": "Slate", "render_hint": "dark grey slate cladding"}}


def test_extract_json_handles_fences_and_prose():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Here you go: [1, 2] thanks') == [1, 2]
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_box_to_quad_scales_and_clamps():
    assert box_to_quad([100, 200, 500, 400], width=1000, height=2000) == [
        [200.0, 200.0], [400.0, 200.0], [400.0, 1000.0], [200.0, 1000.0],
    ]
    assert box_to_quad([-10, 0, 1200, 1000], 100, 100)[2] == [100.0, 100.0]


def test_render_prompt_contains_constraints_and_targets():
    components = [{"id": "c1", "type": "pillar", "quad": [[100, 0], [200, 0], [200, 500], [100, 500]]}]
    spec = {"style": "modern", "assignments": [
        {"target": "component:c1", "material_id": "slate", "color": None, "finish": "natural"},
        {"target": "type:wall", "material_id": "slate", "color": "#333333", "finish": ""},
    ], "keep_unchanged": ["window"]}
    prompt = build_render_prompt(spec, components, CATALOG, width=1000, height=1000)
    payload = json.loads(prompt.split("\n", 1)[1])

    assert any("camera angle" in c for c in payload["hard_constraints"])
    assert payload["changes"][0]["apply_to"] == "the pillar inside the box x 10%-20%, y 0%-50% of the image"
    assert payload["changes"][1]["apply_to"] == "every wall surface"
    assert payload["changes"][1]["material"] == "dark grey slate cladding"
    assert payload["keep_unchanged"] == ["window"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest core/tests/test_ai_helpers.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.ai'`.

- [ ] **Step 3: Implement**

`backend/core/ai.py`:
```python
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
```

- [ ] **Step 4: Run tests**

Run: `pytest core/tests/test_ai_helpers.py`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
cd .. && git add backend/core && git commit -m "feat: add AI prompt and parsing helpers

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: AI service — Vertex calls

**Files:**
- Modify: `backend/core/ai.py`
- Test: `backend/core/tests/test_ai_calls.py`

**Interfaces:**
- Produces (all raise `AiUnavailable` on failure; managers mock these in tests):
  - `check_photo(image_bytes, mime) -> {"is_house_exterior": bool, "facade_visible": bool, "issues": list[str], "tips": list[str]}`
  - `detect_structure(image_bytes, mime, width, height) -> list[{"type", "quad", "floor", "confidence"}]`
  - `parse_text(text, present_types: list[str], catalog: dict) -> dict` (raw spec + optional `"notes": list[str]`)
  - `recommend(answers: dict, shortlist: list[dict], present_types: list[str]) -> list[{"name", "rationale", "spec"}]`
  - `search_rates(state, city, items: list[dict]) -> list[{"material_id", "material_rate", "labor_rate", "sources"}]`
  - `render(image_bytes, mime, prompt) -> bytes` (PNG)

- [ ] **Step 1: Write the failing test** (mocks the SDK client; live behaviour is checked in Task 13)

`backend/core/tests/test_ai_calls.py`:
```python
from types import SimpleNamespace

import pytest

from core import ai


class FakeModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def fake_client(monkeypatch, *responses):
    models = FakeModels(responses)
    monkeypatch.setattr(ai, "client", lambda: SimpleNamespace(models=models))
    monkeypatch.setattr(ai, "RETRY_DELAY_SECONDS", 0)
    return models


def text_response(text):
    return SimpleNamespace(text=text, candidates=[SimpleNamespace(grounding_metadata=None)])


def test_detect_structure_filters_unknown_types(monkeypatch):
    fake_client(monkeypatch, text_response(
        '{"components": [{"type": "wall", "box_2d": [0, 0, 500, 1000], "floor": 0, "confidence": 0.9},'
        ' {"type": "car", "box_2d": [0, 0, 10, 10]}]}'
    ))
    found = ai.detect_structure(b"img", "image/jpeg", 1000, 800)
    assert found == [{"type": "wall", "quad": [[0.0, 0.0], [1000.0, 0.0], [1000.0, 400.0], [0.0, 400.0]],
                      "floor": 0, "confidence": 0.9}]


def test_retry_once_then_unavailable(monkeypatch):
    models = fake_client(monkeypatch, RuntimeError("boom"), RuntimeError("boom"))
    with pytest.raises(ai.AiUnavailable):
        ai.check_photo(b"img", "image/jpeg")
    assert models.calls == 2


def test_search_rates_attaches_grounding_sources(monkeypatch):
    chunk = SimpleNamespace(web=SimpleNamespace(uri="https://example.in/rates"))
    response = SimpleNamespace(
        text='{"rates": [{"material_id": "x", "material_rate": 20, "labor_rate": 10}]}',
        candidates=[SimpleNamespace(grounding_metadata=SimpleNamespace(grounding_chunks=[chunk]))],
    )
    fake_client(monkeypatch, response)
    rows = ai.search_rates("Maharashtra", "Pune", [{"id": "x", "name": "X", "rate_unit": "sqft"}])
    assert rows == [{"material_id": "x", "material_rate": 20, "labor_rate": 10, "sources": ["https://example.in/rates"]}]


def test_render_returns_image_bytes(monkeypatch):
    part = SimpleNamespace(inline_data=SimpleNamespace(data=b"\x89PNG"))
    fake_client(monkeypatch, SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))]))
    assert ai.render(b"img", "image/jpeg", "prompt") == b"\x89PNG"
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest core/tests/test_ai_calls.py`
Expected: FAIL — `AttributeError: module 'core.ai' has no attribute 'client'`.

- [ ] **Step 3: Implement**

Append to `backend/core/ai.py`:
```python
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
            time.sleep(RETRY_DELAY_SECONDS)
    raise AiUnavailable() from last_error


def _json_call(contents, temperature=0.2, tools=None):
    config = types.GenerateContentConfig(temperature=temperature, tools=tools)
    if tools is None:
        config.response_mime_type = "application/json"
    response = _generate(settings.MODEL_TEXT, contents, config)
    try:
        return extract_json(response.text), response
    except ValueError as exc:
        logger.warning("Unreadable Gemini JSON: %s", exc)
        raise AiUnavailable("The AI returned an unreadable answer. Try again.") from exc


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
        "issues": [str(i) for i in data.get("issues", [])][:3],
        "tips": [str(t) for t in data.get("tips", [])][:3],
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
    for c in data.get("components", []):
        box = c.get("box_2d")
        if c.get("type") in COMPONENT_TYPES and isinstance(box, list) and len(box) == 4:
            found.append({
                "type": c["type"],
                "quad": box_to_quad(box, width, height),
                "floor": int(c.get("floor") or 0),
                "confidence": c.get("confidence"),
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
    return [d for d in data.get("designs", []) if isinstance(d, dict)][:3]


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
    for r in data.get("rates", []) if isinstance(data, dict) else []:
        if isinstance(r, dict):
            rows.append({
                "material_id": r.get("material_id"),
                "material_rate": r.get("material_rate"),
                "labor_rate": r.get("labor_rate"),
                "sources": (r.get("sources") or fallback_sources)[:MAX_SOURCES],
            })
    return rows


def render(image_bytes, mime, prompt):
    config = types.GenerateContentConfig(response_modalities=["IMAGE"])
    response = _generate(settings.MODEL_IMAGE, [_image_part(image_bytes, mime), prompt], config)
    for candidate in response.candidates or []:
        for part in candidate.content.parts or []:
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                return inline.data
    raise AiUnavailable("The image model returned no picture. Try again.")
```

- [ ] **Step 4: Run tests**

Run: `pytest core/tests/test_ai_calls.py core/tests/test_ai_helpers.py`
Expected: `7 passed`.

- [ ] **Step 5: Commit**

```bash
cd .. && git add backend/core && git commit -m "feat: add Vertex Gemini calls for detection, design, rates and render

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Rates manager

**Files:**
- Create: `backend/core/managers/__init__.py` (empty), `backend/core/managers/rates.py`
- Test: `backend/core/tests/test_rates.py`

**Interfaces:**
- Consumes: `load_catalog`, `city_tier` (Task 3), `ai.search_rates` (Task 7), models (Task 2).
- Produces: `get_rates(state, city, project_id=None) -> dict[material_id, row]` (row keys: `material_id, rate_unit, material_rate, labor_rate, source ('web'|'estimated'|'override'), sources, fetched_at`), `set_override(project_id, material_id, material_rate, labor_rate) -> None`, `TIER_MULTIPLIER`.

- [ ] **Step 1: Write the failing tests**

`backend/core/tests/test_rates.py`:
```python
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from core import ai
from core.catalog import load_catalog
from core.errors import AppError
from core.managers import rates
from core.models import RateCache

PAINT = "exterior_emulsion"


def web_rows(material_rate, labor_rate):
    return [{"material_id": PAINT, "material_rate": material_rate, "labor_rate": labor_rate, "sources": ["https://a.in"]}]


@pytest.mark.django_db
def test_web_rate_within_bounds_is_used_and_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(ai, "search_rates", lambda s, c, items: calls.append(1) or web_rows(20, 11))

    result = rates.get_rates("Maharashtra", "Pune")
    assert result[PAINT]["material_rate"] == 20
    assert result[PAINT]["source"] == "web"
    rates.get_rates("Maharashtra", "Pune")
    assert calls == [1]  # second call served from cache


@pytest.mark.django_db
def test_out_of_bounds_web_rate_falls_back_to_tier(monkeypatch):
    monkeypatch.setattr(ai, "search_rates", lambda s, c, items: web_rows(9999, 11))
    result = rates.get_rates("Maharashtra", "Pune")  # tier 1
    base = load_catalog()[PAINT]
    assert result[PAINT]["source"] == "estimated"
    assert result[PAINT]["material_rate"] == round(base["base_material_rate"] * rates.TIER_MULTIPLIER[1])


@pytest.mark.django_db
def test_ai_failure_falls_back(monkeypatch):
    def boom(*args):
        raise ai.AiUnavailable()

    monkeypatch.setattr(ai, "search_rates", boom)
    result = rates.get_rates("Kerala", "Thrissur")
    assert all(r["source"] == "estimated" for r in result.values())


@pytest.mark.django_db
def test_stale_cache_is_refetched(monkeypatch):
    monkeypatch.setattr(ai, "search_rates", lambda s, c, items: web_rows(20, 11))
    rates.get_rates("Maharashtra", "Pune")
    RateCache.objects.update(fetched_at=timezone.now() - timedelta(days=31))
    monkeypatch.setattr(ai, "search_rates", lambda s, c, items: web_rows(22, 12))
    assert rates.get_rates("Maharashtra", "Pune")[PAINT]["material_rate"] == 22


@pytest.mark.django_db
def test_no_city_uses_tier_two_without_ai(monkeypatch):
    monkeypatch.setattr(ai, "search_rates", lambda *a: pytest.fail("should not call AI"))
    result = rates.get_rates("", "")
    assert result[PAINT]["material_rate"] == load_catalog()[PAINT]["base_material_rate"]


@pytest.mark.django_db
def test_override_wins(monkeypatch):
    monkeypatch.setattr(ai, "search_rates", lambda s, c, items: web_rows(20, 11))
    project_id = uuid.uuid4()
    rates.set_override(project_id, PAINT, material_rate=30, labor_rate=None)
    row = rates.get_rates("Maharashtra", "Pune", project_id=project_id)[PAINT]
    assert row["material_rate"] == 30
    assert row["labor_rate"] == 11
    assert row["source"] == "override"


@pytest.mark.django_db
def test_override_validation():
    with pytest.raises(AppError):
        rates.set_override(uuid.uuid4(), "nope", 10, 10)
    with pytest.raises(AppError):
        rates.set_override(uuid.uuid4(), PAINT, -5, None)
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest core/tests/test_rates.py`
Expected: FAIL — `ImportError: cannot import name 'rates' from 'core.managers'`.

- [ ] **Step 3: Implement**

`backend/core/managers/__init__.py`: empty file.

`backend/core/managers/rates.py`:
```python
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from core import ai
from core.catalog import city_tier, load_catalog
from core.errors import AppError
from core.models import RateCache, RateOverride

logger = logging.getLogger(__name__)
TIER_MULTIPLIER = {1: 1.2, 2: 1.0, 3: 0.85}
BOUND_LOW = 0.3
BOUND_HIGH = 3.0


def _fallback(item, tier):
    m = TIER_MULTIPLIER[tier]
    return {"material_rate": round(item["base_material_rate"] * m), "labor_rate": round(item["base_labor_rate"] * m),
            "source": "estimated", "sources": []}


def _within(value, base):
    return BOUND_LOW * base <= value <= BOUND_HIGH * base


def _validate_web(row, item):
    try:
        material_rate, labor_rate = float(row["material_rate"]), float(row["labor_rate"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (_within(material_rate, item["base_material_rate"]) and _within(labor_rate, item["base_labor_rate"])):
        return None
    return {"material_rate": round(material_rate), "labor_rate": round(labor_rate),
            "source": "web", "sources": [str(s) for s in row.get("sources", [])]}


def _fetch_and_cache(state, city, missing, tier, catalog):
    try:
        rows = ai.search_rates(state, city, missing)
    except ai.AiUnavailable:
        logger.warning("Rate search failed for %s, %s; using tier estimates", city, state)
        rows = []
    web = {}
    for row in rows:
        item = catalog.get(row.get("material_id"))
        valid = _validate_web(row, item) if item else None
        if valid:
            web[item["id"]] = valid
    cached = {}
    for item in missing:
        values = web.get(item["id"]) or _fallback(item, tier)
        obj, _ = RateCache.all_objects.update_or_create(
            state=state, city=city, material_id=item["id"],
            defaults={**values, "fetched_at": timezone.now(), "deleted_at": None},
        )
        cached[item["id"]] = obj
    return cached


def get_rates(state, city, project_id=None):
    catalog = load_catalog()
    tier = city_tier(state, city)
    fresh_after = timezone.now() - timedelta(days=settings.RATE_CACHE_DAYS)
    cached = {r.material_id: r for r in RateCache.objects.filter(state=state, city=city, fetched_at__gte=fresh_after)}
    missing = [item for mid, item in catalog.items() if mid not in cached]
    if missing and city:
        cached.update(_fetch_and_cache(state, city, missing, tier, catalog))

    result = {}
    for mid, item in catalog.items():
        c = cached.get(mid)
        if c:
            row = {"material_rate": c.material_rate, "labor_rate": c.labor_rate, "source": c.source,
                   "sources": c.sources, "fetched_at": c.fetched_at.isoformat()}
        else:
            row = {**_fallback(item, tier), "fetched_at": None}
        result[mid] = {**row, "material_id": mid, "rate_unit": item["rate_unit"]}

    if project_id:
        for o in RateOverride.objects.filter(project_id=project_id):
            row = result.get(o.material_id)
            if row is None:
                continue
            if o.material_rate is not None:
                row["material_rate"] = o.material_rate
            if o.labor_rate is not None:
                row["labor_rate"] = o.labor_rate
            row["source"] = "override"
    return result


def set_override(project_id, material_id, material_rate, labor_rate):
    if material_id not in load_catalog():
        raise AppError("UNKNOWN_MATERIAL", f"Material '{material_id}' is not in the catalog.")
    for value in (material_rate, labor_rate):
        if value is not None and (not isinstance(value, (int, float)) or value <= 0):
            raise AppError("INVALID_RATE", "Rates must be positive numbers.")
    RateOverride.all_objects.update_or_create(
        project_id=project_id, material_id=material_id,
        defaults={"material_rate": material_rate, "labor_rate": labor_rate, "deleted_at": None},
    )
```

- [ ] **Step 4: Run tests**

Run: `pytest core/tests/test_rates.py`
Expected: `7 passed`.

- [ ] **Step 5: Commit**

```bash
cd .. && git add backend/core && git commit -m "feat: add city rate lookup with cache, bounds and overrides

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Projects, photos, structure managers

**Files:**
- Create: `backend/core/managers/projects.py`, `backend/core/managers/photos.py`, `backend/core/managers/structure.py`
- Test: `backend/core/tests/test_photos_structure.py`

**Interfaces:**
- Consumes: models, `ai.check_photo`, `ai.detect_structure`, estimation scale helpers, `load_cities`.
- Produces:
  - `projects.create(name: str|None) -> Project`, `projects.get_project(project_id) -> Project` (400 invalid id / 404), `projects.update(project, name=None, state=None, city=None) -> Project`, `projects.primary_photo(project) -> Photo` (400 `NO_PHOTO`), `projects.read_bytes(photo) -> bytes`
  - `photos.local_quality(img: PIL.Image) -> list[str]`, `photos.upload(project, uploaded_file) -> Photo`, `photos.set_primary(project, photo_id) -> Project`
  - `structure.component_dicts(project) -> list[dict]`, `structure.detect(project) -> list[dict]`, `structure.save(project, items: list[dict]) -> list[dict]`, `structure.set_scale(project, component_id=None, real_height_ft=None, use_default=False) -> Project`

- [ ] **Step 1: Write the failing tests**

`backend/core/tests/test_photos_structure.py`:
```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest core/tests/test_photos_structure.py`
Expected: FAIL — `ImportError: cannot import name 'photos' from 'core.managers'`.

- [ ] **Step 3: Implement**

`backend/core/managers/projects.py`:
```python
import uuid

from core.catalog import load_cities
from core.errors import AppError
from core.models import Photo, Project

MAX_NAME = 80


def parse_id(value, field="id"):
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise AppError("INVALID_ID", f"{field} is not a valid id.")


def create(name=None):
    return Project.objects.create(name=(name or "My house")[:MAX_NAME])


def get_project(project_id):
    project = Project.objects.filter(id=parse_id(project_id, "project_id")).first()
    if project is None:
        raise AppError("NOT_FOUND", "Project not found. Check the link.", status=404)
    return project


def update(project, name=None, state=None, city=None):
    if name is not None:
        project.name = str(name)[:MAX_NAME] or project.name
    if state is not None:
        if state and state not in {s["name"] for s in load_cities()}:
            raise AppError("INVALID_STATE", f"'{state}' is not a state we know.")
        project.state = state
    if city is not None:
        project.city = str(city).strip()[:MAX_NAME]
    project.save()
    return project


def primary_photo(project):
    photo = Photo.objects.filter(id=project.primary_photo_id).first() if project.primary_photo_id else None
    if photo is None:
        raise AppError("NO_PHOTO", "Upload a usable photo of your house first.")
    return photo


def read_bytes(photo):
    with photo.file.open("rb") as f:
        return f.read()
```

`backend/core/managers/photos.py`:
```python
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

from core import ai
from core.errors import AppError
from core.models import Photo

MAX_SIDE = 2048
THUMB_SIDE = 512
JPEG_QUALITY = 90
LOCAL_TIPS = [
    "Stand across the road so the whole front of the house fits in the frame.",
    "Shoot in daylight and hold the phone steady.",
]


def local_quality(img):
    issues = []
    w, h = img.size
    if min(w, h) < settings.MIN_PHOTO_SIDE:
        issues.append(f"Photo is too small ({w}×{h}). Use at least {settings.MIN_PHOTO_SIDE} px on the short side.")
    gray = img.convert("L")
    gray.thumbnail((THUMB_SIDE, THUMB_SIDE))
    if ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).var[0] < settings.BLUR_MIN_VARIANCE:
        issues.append("Photo looks blurry or flat.")
    return issues


def _normalise(data):
    try:
        img = Image.open(BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError):
        raise AppError("INVALID_IMAGE", "That file is not a photo we can read. Upload a JPG, PNG or WEBP.")
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY)
    return img, buf.getvalue()


def upload(project, uploaded):
    if Photo.objects.filter(project_id=project.id).count() >= settings.MAX_PHOTOS:
        raise AppError("PHOTO_LIMIT", f"A project can hold {settings.MAX_PHOTOS} photos. Delete one first.")
    img, jpeg = _normalise(uploaded.read())
    issues = local_quality(img)
    tips = list(LOCAL_TIPS) if issues else []
    ok = not issues
    if ok:
        verdict = ai.check_photo(jpeg, "image/jpeg")
        ok = verdict["is_house_exterior"] and verdict["facade_visible"] and not verdict["issues"]
        issues, tips = verdict["issues"], verdict["tips"]
        if not ok and not issues:
            issues = ["We could not see the front of a house clearly."]
    photo = Photo(project_id=project.id, mime="image/jpeg", width=img.width, height=img.height,
                  quality_ok=ok, quality_report={"issues": issues, "tips": tips})
    photo.file.save(f"{photo.id}.jpg", ContentFile(jpeg), save=False)
    photo.save()
    if ok and project.primary_photo_id is None:
        set_primary(project, photo.id)
    return photo


def set_primary(project, photo_id):
    photo = Photo.objects.filter(id=photo_id, project_id=project.id).first()
    if photo is None:
        raise AppError("NOT_FOUND", "Photo not found in this project.", status=404)
    if not photo.quality_ok:
        raise AppError("PHOTO_NOT_USABLE", "That photo did not pass the quality check. Pick another one.")
    project.primary_photo_id = photo.id
    project.px_per_ft = None
    project.scale_source = "default"
    project.save()
    return project
```

`backend/core/managers/structure.py`:
```python
from django.db import transaction
from django.utils import timezone

from core import ai
from core.errors import AppError
from core.estimation import COMPONENT_TYPES, default_scale, scale_from_component
from core.managers.projects import parse_id, primary_photo, read_bytes
from core.models import Component

MIN_REAL_FT = 1
MAX_REAL_FT = 100


def component_dicts(project):
    qs = Component.objects.filter(project_id=project.id, photo_id=project.primary_photo_id).order_by("created_at")
    return [{"id": str(c.id), "type": c.type, "quad": c.quad, "floor": c.floor, "source": c.source,
             "confidence": c.confidence} for c in qs]


def _refresh_default_scale(project, photo):
    if project.scale_source == "default":
        project.px_per_ft = default_scale(component_dicts(project), photo.height)
        project.save(update_fields=["px_per_ft", "updated_at"])


def detect(project):
    photo = primary_photo(project)
    found = ai.detect_structure(read_bytes(photo), photo.mime, photo.width, photo.height)
    with transaction.atomic():
        Component.objects.filter(project_id=project.id, photo_id=photo.id).update(deleted_at=timezone.now())
        Component.objects.bulk_create([
            Component(project_id=project.id, photo_id=photo.id, type=c["type"], quad=c["quad"],
                      floor=c["floor"], source="ai", confidence=c["confidence"])
            for c in found
        ])
    _refresh_default_scale(project, photo)
    return component_dicts(project)


def _clean_quad(quad, width, height):
    if not isinstance(quad, list) or len(quad) != 4:
        raise AppError("INVALID_REGION", "Each region needs exactly 4 corner points.")
    try:
        return [[min(max(float(x), 0), width), min(max(float(y), 0), height)] for x, y in quad]
    except (TypeError, ValueError):
        raise AppError("INVALID_REGION", "Region corners must be numbers.")


def save(project, items):
    photo = primary_photo(project)
    if not isinstance(items, list):
        raise AppError("INVALID_REGION", "components must be a list.")
    cleaned = []
    for item in items:
        if item.get("type") not in COMPONENT_TYPES:
            raise AppError("INVALID_REGION", f"Unknown part type '{item.get('type')}'.")
        cleaned.append({**item, "quad": _clean_quad(item.get("quad"), photo.width, photo.height)})

    with transaction.atomic():
        existing = {str(c.id): c for c in Component.objects.filter(project_id=project.id, photo_id=photo.id)}
        kept = set()
        for item in cleaned:
            current = existing.get(str(item.get("id")))
            if current:
                changed = current.type != item["type"] or current.quad != item["quad"]
                current.type, current.quad = item["type"], item["quad"]
                current.floor = int(item.get("floor") or 0)
                current.source = "user" if changed else current.source
                current.save()
                kept.add(str(current.id))
            else:
                Component.objects.create(project_id=project.id, photo_id=photo.id, type=item["type"],
                                         quad=item["quad"], floor=int(item.get("floor") or 0), source="user")
        for cid, c in existing.items():
            if cid not in kept:
                c.soft_delete()
    _refresh_default_scale(project, photo)
    return component_dicts(project)


def set_scale(project, component_id=None, real_height_ft=None, use_default=False):
    photo = primary_photo(project)
    if use_default:
        project.scale_source = "default"
        project.px_per_ft = default_scale(component_dicts(project), photo.height)
    else:
        component = Component.objects.filter(id=parse_id(component_id, "component_id"), project_id=project.id).first()
        if component is None:
            raise AppError("NOT_FOUND", "Part not found.", status=404)
        if not isinstance(real_height_ft, (int, float)) or not MIN_REAL_FT <= real_height_ft <= MAX_REAL_FT:
            raise AppError("INVALID_SCALE", f"Enter a height between {MIN_REAL_FT} and {MAX_REAL_FT} ft.")
        try:
            project.px_per_ft = scale_from_component(component.quad, real_height_ft)
        except ValueError:
            raise AppError("INVALID_SCALE", "That part has no height on the photo. Pick another one.")
        project.scale_source = "user"
    project.save()
    return project
```

- [ ] **Step 4: Run tests**

Run: `pytest core/tests/test_photos_structure.py`
Expected: `8 passed`. If `test_local_quality_flags_small_and_flat` fails on the noisy image, print `ImageStat.Stat(...).var[0]` for both images and set `BLUR_MIN_VARIANCE` midway between the flat (≈0) and noisy values.

- [ ] **Step 5: Commit**

```bash
cd .. && git add backend/core && git commit -m "feat: add photo quality gate, part detection and scale calibration

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Designs manager

**Files:**
- Create: `backend/core/managers/designs.py`
- Test: `backend/core/tests/test_designs.py`

**Interfaces:**
- Consumes: `load_catalog`, `component_dicts`, `primary_photo`, `read_bytes`, `ai.parse_text`, `ai.recommend`, `ai.build_render_prompt`, `ai.render`.
- Produces: `validate_spec(spec, catalog, components) -> (clean_spec, warnings)`, `shortlist(answers, catalog) -> list[item]`, `validate_answers(answers) -> dict`, `from_text(project, text) -> Design`, `recommend(project, answers) -> list[Design]`, `save(project, design_id, name, spec) -> Design`, `get_design(design_id) -> Design`, `render(design) -> Design`, `spec_hash(spec) -> str`.
- Answers schema: `budget ∈ {low, mid, high}`, `climate ∈ {coastal, heavy_rain, hot_dry, moderate}`, `style ∈ {modern, traditional, minimal, luxe}`, `maintenance ∈ {low, medium}`, `color_mood: str ≤ 60`, `keep_unchanged: list[type]`.

- [ ] **Step 1: Write the failing tests**

`backend/core/tests/test_designs.py`:
```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest core/tests/test_designs.py`
Expected: FAIL — `ImportError: cannot import name 'designs' from 'core.managers'`.

- [ ] **Step 3: Implement**

`backend/core/managers/designs.py`:
```python
import hashlib
import json
import re

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import F

from core import ai
from core.catalog import load_catalog
from core.errors import AppError
from core.estimation import COMPONENT_TYPES
from core.managers.projects import parse_id, primary_photo, read_bytes
from core.managers.structure import component_dicts
from core.models import Design, Project

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
MAX_PALETTE = 4
MAX_TEXT = 1000
MIN_TEXT = 3
MAX_DESIGNS_PER_REQUEST = 3
ANSWER_CHOICES = {
    "budget": {"low", "mid", "high"},
    "climate": {"coastal", "heavy_rain", "hot_dry", "moderate"},
    "style": {"modern", "traditional", "minimal", "luxe"},
    "maintenance": {"low", "medium"},
}
EXCLUDED_BUDGETS = {"low": {"high"}, "mid": set(), "high": set()}


def validate_spec(spec, catalog, components):
    if not isinstance(spec, dict) or not isinstance(spec.get("assignments"), list):
        raise AppError("INVALID_SPEC", "A design needs a list of assignments.")
    type_by_id = {str(c["id"]): c["type"] for c in components}
    present = set(type_by_id.values())
    clean, warnings = [], []
    for a in spec["assignments"]:
        if not isinstance(a, dict):
            continue
        target, item = str(a.get("target", "")), catalog.get(a.get("material_id"))
        if item is None:
            warnings.append(f"Material '{a.get('material_id')}' is not in the catalog; skipped.")
            continue
        if target.startswith("type:"):
            ctype = target[len("type:"):]
            if ctype not in present:
                warnings.append(f"No {ctype.replace('_', ' ')} found on this house; {item['name']} skipped.")
                continue
        elif target.startswith("component:"):
            ctype = type_by_id.get(target[len("component:"):])
            if ctype is None:
                warnings.append(f"A selected part no longer exists; {item['name']} skipped.")
                continue
        else:
            warnings.append(f"Unknown target '{target}'; skipped.")
            continue
        if ctype not in item["applies_to"]:
            warnings.append(f"{item['name']} is not used on {ctype.replace('_', ' ')}; skipped.")
            continue
        color = a.get("color")
        clean.append({"target": target, "material_id": item["id"],
                      "color": color if isinstance(color, str) and HEX.match(color) else None,
                      "finish": str(a.get("finish") or "")[:40]})
    palette = [c for c in spec.get("palette", []) if isinstance(c, str) and HEX.match(c)][:MAX_PALETTE]
    keep = [t for t in spec.get("keep_unchanged", []) if t in COMPONENT_TYPES]
    return {"style": str(spec.get("style") or "")[:30], "palette": palette,
            "assignments": clean, "keep_unchanged": keep}, warnings


def validate_answers(answers):
    if not isinstance(answers, dict):
        raise AppError("INVALID_ANSWERS", "Answers must be an object.")
    clean = {}
    for key, choices in ANSWER_CHOICES.items():
        value = answers.get(key)
        if value not in choices:
            raise AppError("INVALID_ANSWERS", f"Pick one of {sorted(choices)} for {key}.")
        clean[key] = value
    clean["color_mood"] = str(answers.get("color_mood") or "")[:60]
    clean["keep_unchanged"] = [t for t in answers.get("keep_unchanged") or [] if t in COMPONENT_TYPES]
    return clean


def shortlist(answers, catalog):
    items = [
        i for i in catalog.values()
        if answers["climate"] in i["climates"]
        and not (answers["maintenance"] == "low" and i["maintenance"] == "high")
        and i["budget"] not in EXCLUDED_BUDGETS[answers["budget"]]
    ]
    return items or list(catalog.values())


def spec_hash(spec):
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()


def get_design(design_id):
    design = Design.objects.filter(id=parse_id(design_id, "design_id")).first()
    if design is None:
        raise AppError("NOT_FOUND", "Design not found.", status=404)
    return design


def _present_types(components):
    return sorted({c["type"] for c in components})


def from_text(project, text):
    text = str(text or "").strip()
    if not MIN_TEXT <= len(text) <= MAX_TEXT:
        raise AppError("INVALID_TEXT", f"Describe the design in {MIN_TEXT}-{MAX_TEXT} characters.")
    components, catalog = component_dicts(project), load_catalog()
    raw = ai.parse_text(text, _present_types(components), catalog)
    spec, warnings = validate_spec(raw, catalog, components)
    notes = [str(n) for n in raw.get("notes", [])] if isinstance(raw, dict) else []
    return Design.objects.create(project_id=project.id, name="Your description", mode="free_text",
                                 input={"text": text}, spec=spec, warnings=notes + warnings)


def recommend(project, answers):
    answers = validate_answers(answers)
    components, catalog = component_dicts(project), load_catalog()
    proposals = ai.recommend(answers, shortlist(answers, catalog), _present_types(components))
    created = []
    for p in proposals[:MAX_DESIGNS_PER_REQUEST]:
        raw = p.get("spec") or {}
        if isinstance(raw, dict):
            raw.setdefault("keep_unchanged", answers["keep_unchanged"])
        spec, warnings = validate_spec(raw, catalog, components)
        created.append(Design.objects.create(
            project_id=project.id, name=str(p.get("name") or "Suggested design")[:60], mode="guided",
            input=answers, spec=spec, rationale=str(p.get("rationale") or "")[:600], warnings=warnings,
        ))
    if not created:
        raise AppError("NO_SUGGESTIONS", "We could not suggest designs. Try different answers or describe it yourself.")
    return created


def save(project, design_id, name, spec):
    spec, warnings = validate_spec(spec, load_catalog(), component_dicts(project))
    if design_id:
        design = get_design(design_id)
        if design.project_id != project.id:
            raise AppError("NOT_FOUND", "Design not found.", status=404)
        design.name, design.spec, design.warnings = str(name or design.name)[:60], spec, warnings
        design.save()
        return design
    return Design.objects.create(project_id=project.id, name=str(name or "My design")[:60], mode="manual",
                                 spec=spec, warnings=warnings)


def render(design):
    current_hash = spec_hash(design.spec)
    if design.render_file and design.render_spec_hash == current_hash:
        return design
    project = Project.objects.get(id=design.project_id)
    claimed = Project.objects.filter(id=project.id, render_count__lt=settings.RENDER_CAP).update(
        render_count=F("render_count") + 1)
    if not claimed:
        raise AppError("RENDER_LIMIT", f"This project has used all {settings.RENDER_CAP} previews.", status=429)
    try:
        photo = primary_photo(project)
        prompt = ai.build_render_prompt(design.spec, component_dicts(project), load_catalog(), photo.width, photo.height)
        png = ai.render(read_bytes(photo), photo.mime, prompt)
    except AppError:
        Project.objects.filter(id=project.id).update(render_count=F("render_count") - 1)
        raise
    design.render_file.save(f"{design.id}-{current_hash[:8]}.png", ContentFile(png), save=False)
    design.render_spec_hash = current_hash
    design.save()
    return design
```

Note: `ai.AiUnavailable` subclasses `AppError`, so the refund branch covers AI failures.

- [ ] **Step 4: Run tests**

Run: `pytest core/tests/test_designs.py`
Expected: `8 passed`.

- [ ] **Step 5: Commit**

```bash
cd .. && git add backend/core && git commit -m "feat: add design spec validation, suggestions and capped rendering

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Estimates + PDF report

**Files:**
- Create: `backend/core/managers/estimates.py`, `backend/core/managers/report.py`
- Test: `backend/core/tests/test_report.py`

**Interfaces:**
- Consumes: `estimate`, `default_scale`, `walls_overlap_warnings`, `rates.get_rates`, `component_dicts`, `primary_photo`.
- Produces: `estimates.for_design(design) -> dict` (Task 5 shape + `location{state, city}`), `report.inr(amount) -> str`, `report.build_pdf(project_name, design_name, estimate, materials: list[str], original_path: str|None, render_path: str|None) -> bytes`, `report.for_design(design) -> bytes`.

- [ ] **Step 1: Write the failing tests**

`backend/core/tests/test_report.py`:
```python
from core.managers.report import build_pdf, inr

ESTIMATE = {
    "scale": {"px_per_ft": 20, "source": "default"},
    "lines": [{"category": "Paint", "name": "Exterior emulsion paint", "material_id": "exterior_emulsion",
               "targets": ["wall×2"], "measure": 812.4, "rate_unit": "sqft", "quantity": 15.5, "qty_unit": "L",
               "wastage_pct": 5, "material_rate": 16, "labor_rate": 10, "rate_source": "web",
               "material_cost": 13648, "labor_cost": 8124, "total": 21772}],
    "grand_total": 21772,
    "assumptions": ["Only the visible facade is measured."],
    "warnings": [],
    "location": {"state": "Maharashtra", "city": "Pune"},
}


def test_inr_grouping():
    assert inr(999) == "Rs 999"
    assert inr(1000) == "Rs 1,000"
    assert inr(184500) == "Rs 1,84,500"
    assert inr(12345678) == "Rs 1,23,45,678"


def test_pdf_bytes():
    pdf = build_pdf("My house", "Modern slate", ESTIMATE, ["Exterior emulsion paint on wall"], None, None)
    assert pdf.startswith(b"%PDF")
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest core/tests/test_report.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.managers.report'`.

- [ ] **Step 3: Implement**

`backend/core/managers/estimates.py`:
```python
from core.catalog import load_catalog
from core.estimation import default_scale, estimate, walls_overlap_warnings
from core.managers import rates
from core.managers.projects import primary_photo
from core.managers.structure import component_dicts
from core.models import Project


def for_design(design):
    project = Project.objects.get(id=design.project_id)
    photo = primary_photo(project)
    components = component_dicts(project)
    px_per_ft = project.px_per_ft or default_scale(components, photo.height)
    rate_rows = rates.get_rates(project.state, project.city, project_id=project.id)
    result = estimate(components, design.spec, load_catalog(), rate_rows, px_per_ft, project.scale_source)
    result["warnings"] = walls_overlap_warnings(components) + result["warnings"]
    result["location"] = {"state": project.state, "city": project.city}
    return result
```

`backend/core/managers/report.py`:
```python
from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.catalog import load_catalog
from core.managers import estimates
from core.managers.projects import primary_photo
from core.models import Project

IMAGE_WIDTH = 85 * mm
INK = colors.HexColor("#1f2a37")
RULE = colors.HexColor("#d5dbe3")
DISCLAIMER = ("Advisory estimate generated from one photo. Areas are approximate and rates are averages; "
              "confirm measurements and prices with your contractor before work begins.")


def inr(amount):
    digits = str(int(round(abs(amount))))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups) + "," + tail
    return ("-" if amount < 0 else "") + "Rs " + digits


def _image(path):
    img = Image(path)
    img.drawHeight = IMAGE_WIDTH * img.imageHeight / img.imageWidth
    img.drawWidth = IMAGE_WIDTH
    return img


def build_pdf(project_name, design_name, estimate, materials, original_path, render_path):
    styles = getSampleStyleSheet()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm, title=f"{project_name} - renovation estimate")
    loc = estimate.get("location") or {}
    where = ", ".join(v for v in (loc.get("city"), loc.get("state")) if v) or "Location not set"
    story = [
        Paragraph(f"{project_name}: exterior renovation estimate", styles["Title"]),
        Paragraph(f"Design: {design_name} &middot; {where} &middot; "
                  f"{datetime.now(timezone.utc):%d %b %Y}", styles["Normal"]),
        Spacer(1, 6 * mm),
    ]
    images = [[_image(p) if p else Paragraph("No image", styles["Normal"]) for p in (original_path, render_path)]]
    if original_path or render_path:
        story += [Table([["Original", "Redesigned"]] + images, colWidths=[IMAGE_WIDTH + 4 * mm] * 2),
                  Spacer(1, 6 * mm)]

    story.append(Paragraph("Selected materials", styles["Heading2"]))
    story += [Paragraph(f"&bull; {m}", styles["Normal"]) for m in materials] or [Paragraph("None", styles["Normal"])]
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Quantities and cost", styles["Heading2"]))
    rows = [["Item", "Area / length", "Quantity", "Rate (mat + lab)", "Material", "Labour", "Total"]]
    for line in estimate["lines"]:
        rows.append([
            Paragraph(f"{line['name']}<br/><font size=7>{', '.join(line['targets'])} &middot; "
                      f"{line['rate_source']}</font>", styles["BodyText"]),
            f"{line['measure']} {line['rate_unit']}",
            f"{line['quantity']} {line['qty_unit']}",
            f"{line['material_rate']} + {line['labor_rate']} /{line['rate_unit']}",
            inr(line["material_cost"]), inr(line["labor_cost"]), inr(line["total"]),
        ])
    rows.append(["Grand total", "", "", "", "", "", inr(estimate["grand_total"])])
    table = Table(rows, colWidths=[48 * mm, 22 * mm, 20 * mm, 28 * mm, 20 * mm, 20 * mm, 22 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, 0), 1, INK),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, RULE),
        ("LINEABOVE", (0, -1), (-1, -1), 1, INK),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story += [table, Spacer(1, 6 * mm), Paragraph("Assumptions", styles["Heading2"])]
    story += [Paragraph(f"&bull; {a}", styles["Normal"]) for a in estimate["assumptions"] + estimate["warnings"]]
    story += [Spacer(1, 6 * mm), Paragraph(DISCLAIMER, styles["Italic"])]
    doc.build(story)
    return buf.getvalue()


def for_design(design):
    project = Project.objects.get(id=design.project_id)
    photo = primary_photo(project)
    catalog = load_catalog()
    materials = [
        f"{catalog[a['material_id']]['name']} on {a['target'].split(':', 1)[1].replace('_', ' ')}"
        + (f" ({a['color']})" if a.get("color") else "")
        for a in design.spec.get("assignments", []) if a["material_id"] in catalog
    ]
    render_path = design.render_file.path if design.render_file else None
    return build_pdf(project.name, design.name, estimates.for_design(design), materials,
                     photo.file.path, render_path)
```

Component targets in `materials` show the component UUID; that is acceptable for v1 because the PDF table already lists the measured part types. (Frontend plan names targets by type in the UI.)

- [ ] **Step 4: Run tests**

Run: `pytest core/tests/test_report.py`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
cd .. && git add backend/core && git commit -m "feat: add estimate assembly and PDF report

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Serializers, views, URLs + API flow test

**Files:**
- Create: `backend/core/serializers.py`, `backend/core/views.py`
- Modify: `backend/core/urls.py` (replace)
- Test: `backend/core/tests/test_api.py`

**Interfaces (frozen contract for the frontend plan):**

| Method | Path | Body / query | 200 response |
|---|---|---|---|
| POST | `/api/project/create` | `{name?}` | project |
| GET | `/api/project?id=` | | project |
| POST | `/api/project/update?id=` | `{name?, state?, city?}` | project |
| POST | `/api/photo/upload?project_id=` | multipart `file` | project |
| POST | `/api/photo/set-primary?project_id=` | `{photo_id}` | project |
| POST | `/api/structure/detect?project_id=` | | project |
| POST | `/api/structure/save?project_id=` | `{components:[{id?, type, quad, floor?}]}` | project |
| POST | `/api/scale/set?project_id=` | `{component_id, real_height_ft}` or `{use_default: true}` | project |
| GET | `/api/catalog` | | `{materials: [...]}` |
| GET | `/api/locations` | | `{states: [{name, cities:[{name, tier}]}]}` |
| GET | `/api/rates?state=&city=&project_id=?` | | `{rates: [row]}` |
| POST | `/api/rates/override?project_id=` | `{material_id, material_rate?, labor_rate?}` | `{rates: [row]}` |
| POST | `/api/design/from-text?project_id=` | `{text}` | `{designs: [design]}` |
| POST | `/api/design/recommend?project_id=` | answers | `{designs: [design]}` |
| POST | `/api/design/save?project_id=` | `{id?, name, spec}` | `{designs: [design]}` |
| POST | `/api/design/render?id=` | | design |
| GET | `/api/estimate?design_id=` | | estimate |
| GET | `/api/report?design_id=` | | `application/pdf` |

`project` = `{id, name, state, city, px_per_ft, scale_source, primary_photo_id, render_count, render_cap, photos:[{id, url, width, height, quality_ok, issues, tips}], components:[component], designs:[design]}`.
`design` = `{id, name, mode, input, spec, rationale, warnings, render_url, created_at}`.

- [ ] **Step 1: Write the failing test**

`backend/core/tests/test_api.py`:
```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest core/tests/test_api.py`
Expected: FAIL — 404s on every route (`assert 404 == 200`).

- [ ] **Step 3: Implement**

`backend/core/serializers.py`:
```python
from django.conf import settings

from core.managers.structure import component_dicts
from core.models import Design, Photo


def _url(request, f):
    return request.build_absolute_uri(f.url) if f else None


def photo_dict(request, p):
    return {"id": str(p.id), "url": _url(request, p.file), "width": p.width, "height": p.height,
            "quality_ok": p.quality_ok, "issues": p.quality_report.get("issues", []),
            "tips": p.quality_report.get("tips", [])}


def design_dict(request, d):
    return {"id": str(d.id), "name": d.name, "mode": d.mode, "input": d.input, "spec": d.spec,
            "rationale": d.rationale, "warnings": d.warnings, "render_url": _url(request, d.render_file),
            "created_at": d.created_at.isoformat()}


def project_dict(request, project):
    photos = Photo.objects.filter(project_id=project.id).order_by("created_at")
    designs = Design.objects.filter(project_id=project.id).order_by("-created_at")
    return {
        "id": str(project.id), "name": project.name, "state": project.state, "city": project.city,
        "px_per_ft": project.px_per_ft, "scale_source": project.scale_source,
        "primary_photo_id": str(project.primary_photo_id) if project.primary_photo_id else None,
        "render_count": project.render_count, "render_cap": settings.RENDER_CAP,
        "photos": [photo_dict(request, p) for p in photos],
        "components": component_dicts(project) if project.primary_photo_id else [],
        "designs": [design_dict(request, d) for d in designs],
    }
```

`backend/core/views.py`:
```python
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.catalog import load_catalog, load_cities
from core.errors import AppError
from core.managers import designs, estimates, photos, projects, rates, report, structure
from core.serializers import design_dict, project_dict


def _project(request, key="project_id"):
    return projects.get_project(request.query_params.get(key))


@api_view(["POST"])
def project_create(request):
    return Response(project_dict(request, projects.create(request.data.get("name"))))


@api_view(["GET"])
def project_get(request):
    return Response(project_dict(request, _project(request, "id")))


@api_view(["POST"])
def project_update(request):
    project = projects.update(_project(request, "id"), name=request.data.get("name"),
                              state=request.data.get("state"), city=request.data.get("city"))
    return Response(project_dict(request, project))


@api_view(["POST"])
def photo_upload(request):
    project = _project(request)
    uploaded = request.FILES.get("file")
    if uploaded is None:
        raise AppError("NO_FILE", "Choose a photo to upload.")
    photos.upload(project, uploaded)
    project.refresh_from_db()
    return Response(project_dict(request, project))


@api_view(["POST"])
def photo_set_primary(request):
    project = photos.set_primary(_project(request), projects.parse_id(request.data.get("photo_id"), "photo_id"))
    return Response(project_dict(request, project))


@api_view(["POST"])
def structure_detect(request):
    project = _project(request)
    structure.detect(project)
    project.refresh_from_db()
    return Response(project_dict(request, project))


@api_view(["POST"])
def structure_save(request):
    project = _project(request)
    structure.save(project, request.data.get("components"))
    project.refresh_from_db()
    return Response(project_dict(request, project))


@api_view(["POST"])
def scale_set(request):
    project = structure.set_scale(
        _project(request), component_id=request.data.get("component_id"),
        real_height_ft=request.data.get("real_height_ft"), use_default=bool(request.data.get("use_default")),
    )
    return Response(project_dict(request, project))


@api_view(["GET"])
def catalog(request):
    return Response({"materials": list(load_catalog().values())})


@api_view(["GET"])
def locations(request):
    return Response({"states": load_cities()})


@api_view(["GET"])
def rates_get(request):
    pid = request.query_params.get("project_id")
    project_id = projects.parse_id(pid, "project_id") if pid else None
    rows = rates.get_rates(request.query_params.get("state", ""), request.query_params.get("city", ""), project_id)
    return Response({"rates": list(rows.values())})


@api_view(["POST"])
def rates_override(request):
    project = _project(request)
    rates.set_override(project.id, request.data.get("material_id"),
                       request.data.get("material_rate"), request.data.get("labor_rate"))
    rows = rates.get_rates(project.state, project.city, project_id=project.id)
    return Response({"rates": list(rows.values())})


@api_view(["POST"])
def design_from_text(request):
    design = designs.from_text(_project(request), request.data.get("text"))
    return Response({"designs": [design_dict(request, design)]})


@api_view(["POST"])
def design_recommend(request):
    created = designs.recommend(_project(request), request.data)
    return Response({"designs": [design_dict(request, d) for d in created]})


@api_view(["POST"])
def design_save(request):
    design = designs.save(_project(request), request.data.get("id"), request.data.get("name"),
                          request.data.get("spec"))
    return Response({"designs": [design_dict(request, design)]})


@api_view(["POST"])
def design_render(request):
    design = designs.render(designs.get_design(request.query_params.get("id")))
    return Response(design_dict(request, design))


@api_view(["GET"])
def estimate_get(request):
    return Response(estimates.for_design(designs.get_design(request.query_params.get("design_id"))))


@api_view(["GET"])
def report_get(request):
    design = designs.get_design(request.query_params.get("design_id"))
    response = HttpResponse(report.for_design(design), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="renovation-estimate-{design.id}.pdf"'
    return response
```

`backend/core/urls.py`:
```python
from django.urls import path

from core import views

urlpatterns = [
    path("project/create", views.project_create),
    path("project", views.project_get),
    path("project/update", views.project_update),
    path("photo/upload", views.photo_upload),
    path("photo/set-primary", views.photo_set_primary),
    path("structure/detect", views.structure_detect),
    path("structure/save", views.structure_save),
    path("scale/set", views.scale_set),
    path("catalog", views.catalog),
    path("locations", views.locations),
    path("rates", views.rates_get),
    path("rates/override", views.rates_override),
    path("design/from-text", views.design_from_text),
    path("design/recommend", views.design_recommend),
    path("design/save", views.design_save),
    path("design/render", views.design_render),
    path("estimate", views.estimate_get),
    path("report", views.report_get),
]
```

- [ ] **Step 4: Run all tests**

Run: `pytest`
Expected: all tests pass (≈ 52 passed), 0 failed.

- [ ] **Step 5: Commit**

```bash
cd .. && git add backend/core && git commit -m "feat: expose renovation API endpoints

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Live Vertex smoke run + tuning

**Files:**
- Create: `backend/scripts/smoke_ai.py`
- Modify (only if needed): `backend/config/settings.py` (`BLUR_MIN_VARIANCE`), prompts in `backend/core/ai.py`

**Interfaces:**
- Consumes: everything above, real ADC credentials (quota project already set to `project-1a771a61-0f54-4d61-b3b`).

- [ ] **Step 1: Get a real test photo**

Ask the user for 1–2 real house-front photos (their own) and save them as `backend/scripts/samples/house1.jpg` (gitignored: add `backend/scripts/samples/` to `.gitignore`). Do not download random images from the web.

- [ ] **Step 2: Write the smoke script**

`backend/scripts/smoke_ai.py`:
```python
"""Live end-to-end run against Vertex. Usage: python scripts/smoke_ai.py scripts/samples/house1.jpg Maharashtra Pune"""
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
    photo = step("upload + quality gate", lambda: photos.upload(project, SimpleUploadedFile("h.jpg", data)))
    print(json.dumps({"ok": photo.quality_ok, **photo.quality_report}, indent=1))
    project.refresh_from_db()
    found = step("detect", lambda: structure.detect(project))
    print({t: sum(c["type"] == t for c in found) for t in {c["type"] for c in found}})
    project.refresh_from_db()
    design = step("free text", lambda: designs.from_text(
        project, "Grey texture paint on walls, slate cladding on pillars, glass railing on balconies"))
    print(json.dumps(design.spec, indent=1), design.warnings)
    guided = step("recommend", lambda: designs.recommend(project, {
        "budget": "mid", "climate": "heavy_rain", "style": "modern", "maintenance": "low"}))
    print([(d.name, d.rationale) for d in guided])
    design = step("render", lambda: designs.render(design))
    print("render:", design.render_file.path)
    est = step("estimate (incl. rate search)", lambda: estimates.for_design(design))
    print(json.dumps({k: est[k] for k in ("scale", "grand_total", "warnings")}, indent=1))
    for line in est["lines"]:
        print(f"  {line['name']}: {line['measure']} {line['rate_unit']} @ {line['material_rate']}+{line['labor_rate']}"
              f" ({line['rate_source']}) = {line['total']}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
```

- [ ] **Step 3: Run it**

Run: `python manage.py migrate && python scripts/smoke_ai.py scripts/samples/house1.jpg Maharashtra Pune`
Expected: every step prints; `ok: true`; detect finds ≥ 1 wall and ≥ 1 window; render path exists; at least some rates print `(web)`; total > 0. Open the render and check the house shape is unchanged.

- [ ] **Step 4: Tune if needed**

- Good photo rejected as blurry → print the edge variance for it and lower `BLUR_MIN_VARIANCE` below that value.
- Detection boxes poor → tighten the `detect_structure` prompt (e.g. "walls: one box per flat wall plane between floors").
- Rates all `estimated` → print the raw `search_rates` rows; widen nothing — check whether the model returned per-sqft numbers or ranges, and fix the prompt.
- Render drifts geometry → strengthen `HARD_CONSTRAINTS`; note any residual drift for `docs/limitations.md` (Plan 3).

Re-run `pytest` after any change. Expected: all pass.

- [ ] **Step 5: Commit**

```bash
cd .. && git add .gitignore backend/scripts/smoke_ai.py backend/config backend/core && git commit -m "chore: add live Vertex smoke run and tune thresholds

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Self-review

**Spec coverage**

| Spec item | Task |
|---|---|
| M1 upload, quality gate, guidance, primary | 9, 12 |
| M2 detection | 7, 9 |
| M3 edit regions (add/move/delete/retype) | 9 (`structure.save`), UI in Plan 2 |
| M4 scale calibration + default | 4, 9 |
| M5 catalog w/ durability, maintenance, suitability | 3 |
| M6 free text + guided → same DesignSpec | 7, 10 |
| M7 per-component assignment + edit | 5 (`component:` targets), 10 (`save`) |
| M8 render, cache, cap; slider in Plan 2 | 6, 7, 10 |
| M9 area per surface | 4 |
| M10 quantities | 5 |
| M11 state/city rates, bounds, cache, fallback | 3, 8 |
| M12 cost breakdown + overrides | 5, 8, 12 |
| M13 PDF | 11 |
| M14 save / reopen by UUID | 2, 12 |
| M15 docs | Plan 3 |
| Edges 1–7, 9–11 | 9, 10, 4, 8, 7, 12 tests |
| Edge 8 (render drift), 12 (last write wins) | documented in Plan 3 |

**Placeholder scan:** none — every code step has full code; Task 13 tuning steps name the exact knob.

**Type consistency:** component dict `{id, type, quad, floor, source, confidence}` used by Tasks 4, 5, 6, 9, 10, 11; rate row keys match between Task 8 producer and Task 5/12 consumers; `AiUnavailable` subclasses `AppError` so Task 10's refund branch and Task 2's handler both catch it.
