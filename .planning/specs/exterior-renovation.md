# Spec: AI Exterior House Renovation & Cost Estimation (Prototype)

**Created**: 2026-10-31
**Status**: draft
**Author**: Mihir Kapildev Tiwari
**Epic**: none
**Source**: `AI-Based Exterior House Renovation & Cost Estimation System.pdf` (E2M assessment, 48h)

---

## Problem

Homeowners can't see how their house will look after exterior renovation, don't know which material suits which part of the house, and get inconsistent contractor quotes (rough areas, arbitrary wastage, unclear labor). Decisions get delayed and budgets overrun.

## Goal

A homeowner uploads one photo of their house front and, in **under 5 minutes**, gets:
1. A realistic redesign of *their* house with chosen materials (structure preserved).
2. Per-surface area + material quantities.
3. A transparent INR cost breakdown (material + labor + wastage) using **city-specific rates**, editable.
4. A downloadable PDF report to discuss with contractors.

Success = graders can complete upload → detect → design → render → estimate → PDF on the live link without help.

## User Stories

- As a **homeowner**, I upload a photo of my house so I can see it redesigned with stone cladding on the pillars and texture paint on walls before spending money.
- As a **homeowner who doesn't know materials**, I answer a few simple questions (budget, climate, style, maintenance) so the system recommends 2–3 material combinations with reasons.
- As a **homeowner who knows what they want**, I type "grey texture paint, wooden panels on the balcony, glass railing" and get exactly that.
- As a **homeowner in Pune**, I pick my state and city so costs reflect local rates, and I can override any rate my contractor quoted.
- As a **contractor/architect** (secondary), I open a shared project link and download the PDF report.

---

## Requirements

### Must-have (maps to PDF §5 + §9)

| # | Req | PDF ref |
|---|-----|---------|
| M1 | Upload 1–5 exterior photos; quality gate each (resolution, blur, "is house exterior + facade visible"); reject with guidance; user picks primary view | 5.1 |
| M2 | AI detects components: `wall, window, door, balcony, pillar, parapet, gate, roof_edge, railing` as labelled quads on the photo | 5.2 |
| M3 | User reviews detected regions on canvas: move/resize corners, change type, delete, add new region | 5.2 |
| M4 | Scale calibration: user picks one region + enters real size (ft) OR accepts default (door 7 ft, floor 10 ft) → px-per-ft | 5.5 |
| M5 | Material catalog (paint, texture finish, stone cladding, tiles, glass railing, metal railing, ACP/wood panels) with coverage, wastage %, durability, maintenance, suitability tags | 5.3 |
| M6 | Two design input modes, both produce the **same `DesignSpec` JSON**: (a) free text → Gemini parse; (b) guided Q&A → rule shortlist + Gemini rationale → 2–3 combos | 5.3 |
| M7 | Assign material + color/finish per component (or component type) manually; edit any design | 5.3 |
| M8 | Render: original photo + DesignSpec → `gemini-3.1-flash-image`, preserve geometry; before/after slider; multiple designs per project, switch between them | 5.4 |
| M9 | Area estimation per surface (deterministic, from quads + scale; walls net of openings) | 5.5 |
| M10 | Quantity calc: paint litres, tile count, cladding sqft, railing rft, panel sqft — incl. wastage & coverage | 5.6 |
| M11 | State → City selector (≈100 Indian cities + "Other"); rates via Gemini + Google Search grounding, sanity-bounded, cached 30 days, fallback base × city tier | 5.7 |
| M12 | Cost breakdown: material, labor, per-category total, grand total; user overrides rates → instant recalc | 5.7 |
| M13 | Downloadable PDF: original + redesigned image, materials, quantities, cost table, assumptions, disclaimer | 5.8 |
| M14 | Save / re-open projects via UUID link (no login) | 6 |
| M15 | Docs: system architecture, user workflow, how estimation works, limitations | 9 |

### Nice-to-have (only if time left)

- N1 Render variants (2 per request), user picks.
- N2 Side-by-side compare of two designs + their costs.
- N3 "Recent projects" list in localStorage.
- N4 `gemini-3-pro-image` "HD render" button.

### Out of scope

- Login/accounts (UUID link covers save + multi-user).
- Video upload, multi-photo stitching, multi-facade combined estimate (one primary view per estimate).
- 3D / depth models, SAM segmentation.
- Marketplace, live supplier APIs, payments.
- Interior, structural engineering (PDF §7).
- Multi-language, non-INR currency, native mobile app (web is responsive).

---

## Architecture

```
React (Vite) ── Cloudflare Pages (free)
     │  HTTPS / JSON
     ▼
Cloudflare Tunnel (free HTTPS)
     ▼
Django REST + Gunicorn ── GCE e2-micro (Always Free, us-central1)
  ├─ SQLite (persistent disk)
  ├─ media/ (photos, renders, PDFs)
  ├─ estimation engine (pure Python, deterministic)
  └─ Vertex AI (project project-1a771a61-0f54-4d61-b3b, location global, VM service account / ADC)
        ├─ gemini-3.5-flash        → quality gate, structure detection, text→spec, Q&A rationale, city rates (Search grounding)
        └─ gemini-3.1-flash-image  → render
```

**Rule:** LLM never does math. Gemini outputs structure/labels/rates; all area, quantity, cost math is plain Python.

### Pipeline

1. Upload → Pillow checks (min 800 px short side, Laplacian-variance blur) → Gemini check (`is_house_exterior`, `facade_visible`, `issues[]`, `tips[]`).
2. Detect → Gemini returns `[{type, box_2d:[ymin,xmin,ymax,xmax] (0–1000), floor, confidence}]` → stored as 4-point quads in image px.
3. User edits quads (react-konva).
4. Scale → px_per_ft.
5. Design → DesignSpec.
6. Render → prompt built from DesignSpec JSON + original image.
7. Estimate → areas → quantities → rates(city, overrides) → costs.
8. Report → WeasyPrint HTML→PDF.

---

## Data Model (Django / SQLite)

All tables: `id UUID pk`, `created_at`, `updated_at`, `deleted_at` (soft delete). Timestamps UTC.

| Model | Fields |
|-------|--------|
| `Project` | `name`, `state`, `city`, `px_per_ft FLOAT null`, `scale_source TEXT (user\|default)`, `primary_photo_id UUID null`, `render_count INT` |
| `Photo` | `project_id`, `file`, `width`, `height`, `quality_ok BOOL`, `quality_report JSON` |
| `Component` | `project_id`, `photo_id`, `type TEXT`, `quad JSON [[x,y]×4]`, `floor INT`, `source TEXT (ai\|user)`, `confidence FLOAT null` |
| `Design` | `project_id`, `name`, `mode TEXT (free_text\|guided\|manual)`, `input JSON` (text or answers), `spec JSON` (DesignSpec), `rationale TEXT`, `render_file null`, `render_spec_hash TEXT` |
| `RateCache` | `state`, `city`, `material_id`, `material_rate`, `labor_rate`, `unit`, `source TEXT (web\|estimated)`, `sources JSON`, `fetched_at` — unique(state, city, material_id) |
| `RateOverride` | `project_id`, `material_id`, `material_rate null`, `labor_rate null` |

Material catalog = versioned `catalog.json` in repo (not a table — read-only, ~15 items).
Cities = `cities.json` `{state: [{city, tier}]}`.

### DesignSpec (shared contract)

```json
{
  "style": "modern",
  "palette": ["#D9D4CC", "#3B3B3B"],
  "assignments": [
    {"target": "type:wall", "material_id": "texture_paint", "color": "#D9D4CC", "finish": "sand"},
    {"target": "component:7f3a...", "material_id": "stone_cladding_slate", "color": null, "finish": "natural"},
    {"target": "type:railing", "material_id": "glass_railing", "color": null, "finish": "frosted"}
  ],
  "keep_unchanged": ["window", "roof_edge"]
}
```
`target` = `type:<component_type>` or `component:<id>`; component-specific beats type.

---

## API (Django REST, RPC-style, snake_case JSON, IDs as query params)

| Method | Path | Body / Query | Returns |
|--------|------|--------------|---------|
| POST | `/api/project/create` | `{name?}` | `{id}` |
| GET | `/api/project?id=` | | project + photos + components + designs |
| POST | `/api/project/update?id=` | `{name?, state?, city?}` | project |
| POST | `/api/photo/upload?project_id=` | multipart `file` | `{id, quality_ok, issues[], tips[]}` |
| POST | `/api/photo/set-primary?project_id=` | `{photo_id}` | project |
| POST | `/api/structure/detect?project_id=` | | `components[]` |
| POST | `/api/structure/save?project_id=` | `{components:[{id?, type, quad, floor}]}` | `components[]` |
| POST | `/api/scale/set?project_id=` | `{component_id, real_height_ft}` or `{use_default:true}` | `{px_per_ft, scale_source}` |
| GET | `/api/catalog` | | materials[] |
| GET | `/api/locations` | | `{state:[city]}` |
| GET | `/api/rates?state=&city=` | | `[{material_id, material_rate, labor_rate, unit, source, sources[], fetched_at}]` |
| POST | `/api/rates/override?project_id=` | `{material_id, material_rate?, labor_rate?}` | rates |
| POST | `/api/design/from-text?project_id=` | `{text}` | design |
| POST | `/api/design/recommend?project_id=` | `{budget, climate, style, maintenance, color_mood, floors, keep_unchanged[]}` | designs[2–3] |
| POST | `/api/design/save?project_id=` | `{id?, name, spec}` | design |
| POST | `/api/design/render?id=` | | `{render_url}` (cached if spec hash unchanged; 429 if `render_count` ≥ 8) |
| GET | `/api/estimate?design_id=` | | estimate (below) |
| GET | `/api/report?design_id=` | | `application/pdf` |

Error shape: `{"error": {"code", "message", "details"}}`.

### Estimate response

```json
{
  "scale": {"px_per_ft": 21.4, "source": "default"},
  "lines": [
    {"category": "Texture paint", "material_id": "texture_paint", "targets": ["wall×3"],
     "area_sqft": 812.4, "quantity": 92.3, "unit": "kg", "wastage_pct": 10,
     "material_rate": 45, "labor_rate": 18, "rate_unit": "sqft", "rate_source": "web",
     "material_cost": 36558, "labor_cost": 14623, "total": 51181}
  ],
  "grand_total": 184500,
  "assumptions": ["Pillars assumed square: 4 × visible width", "..."]
}
```

---

## Estimation Logic

- **Area (sqft)** = shoelace(quad px) / px_per_ft².
- **Wall net** = wall area − Σ(window, door, gate quads whose centroid lies inside wall).
- **Pillar** = visible width ft × height ft × 4 (square column assumption) — flagged in assumptions.
- **Railing** = length rft = quad width ft (rate per rft).
- **Balcony/parapet** = visible face area.
- **Quantities**: paint L = area × coats / coverage_sqft_per_L × (1 + wastage); tiles = ⌈area / tile_area × (1 + wastage)⌉; cladding/panels sqft = area × (1 + wastage); railing rft × (1 + wastage).
- **Cost** = qty-basis × material_rate + area-basis × labor_rate; per category; grand total.
- **Rates priority**: project override → RateCache (≤30 d) → Gemini grounded search (validated 0.3×–3× base) → base × tier (T1 1.2 / T2 1.0 / T3 0.85).

---

## UI (React + Vite)

Wizard with stepper, every step re-enterable:

1. **Upload** — drag-drop, thumbnails with ✓/✗ + tips, pick primary. Location (state → city) here too.
2. **Detect & Fix** — canvas (react-konva) with coloured labelled quads; side list; drag corners, change type dropdown, delete, "+ Add region". Scale card: pick region + enter ft, or "use defaults".
3. **Design** — tabs: *Describe it* (textarea + examples) / *Help me choose* (chip questions) / *Manual* (per-component material picker from catalog cards showing durability/maintenance). Result: design cards with rationale.
4. **Visualize** — render button, before/after slider, design switcher, re-render on change.
5. **Estimate** — table per category, rate source badges (Web · date · links / Estimated · tier), inline editable rates → instant recalc, grand total, assumptions accordion.
6. **Report** — download PDF, copy project link.

States per step: loading (skeleton/progress for AI calls), empty, error with retry, success. Mobile 375 px usable.

---

## Edge Cases

1. Photo not a house / too dark / blurry / < 800 px → rejected with specific tip ("step back so the full front is visible").
2. Gemini detects nothing or garbage boxes → user can add regions manually; flow never blocks.
3. No scale given → defaults used, flagged "approximate" in estimate + PDF.
4. Free text names a material not in catalog ("marble") → mapped to closest catalog item, user told.
5. Free text targets a component that doesn't exist ("glass railing on balcony" but no balcony) → assignment dropped, warning shown.
6. Rate search returns nonsense / out of bounds / API quota hit → fallback tier rate, badge "Estimated".
7. City not in list ("Other") → state tier default, search still attempted.
8. Render drifts geometry → user can regenerate (counts against cap); note in limitations.
9. Render cap reached (8/project) → 429 with friendly message; credit protection.
10. Vertex timeout / 5xx → retry once, then user-facing error with retry button.
11. Overlapping wall quads → area double count; warn when two walls overlap > 20 %.
12. Concurrent edits on same project link → last write wins (documented).

---

## Testing Criteria

Backend (pytest, Gemini mocked):
- Happy: area from quad + scale; wall net subtracts contained window; paint/tile/cladding/railing quantities incl. wastage; cost totals; rate priority chain.
- Edge: zero/degenerate quad → 0 area; no scale → default + flag; out-of-bounds web rate → fallback; override beats cache; render cap → 429; render cache hit when spec hash unchanged; invalid DesignSpec rejected.
- API smoke: create project → upload fixture photo → detect (mock) → save design → estimate → PDF returns `application/pdf`.

Frontend: `npm run build` clean; manual E2E on live link with 2 real house photos.

---

## Dependencies

- Vertex AI enabled on `project-1a771a61-0f54-4d61-b3b` ✅ (`gemini-3.5-flash`, `gemini-3.1-flash-image` verified 2026-10-31).
- Google Search grounding on `gemini-3.5-flash` — verify; if strict JSON schema + search tool not combinable, parse JSON from text.
- Python: Django, djangorestframework, django-cors-headers, google-genai, Pillow, opencv-python-headless (blur), WeasyPrint, pytest.
- JS: React, Vite, react-konva, react-compare-slider (or CSS slider), axios.
- Hosting: Cloudflare Pages, GCE e2-micro + Cloudflare Tunnel.
- Seed data: `catalog.json` (base INR rates), `cities.json` (≈100 cities, tier).

## Risks

- e2-micro 1 GB RAM: WeasyPrint + OpenCV fine; keep Gunicorn workers = 2, add 1 GB swap.
- Quick tunnel URL changes on restart → keep VM up; or named tunnel if domain available.
- Image model geometry drift → strict prompt + regenerate; documented limitation.
