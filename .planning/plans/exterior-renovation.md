# Plan: exterior-renovation

> **Superseded (2026-10-31)** by superpowers-format sub-plans: `exterior-renovation-backend.md` (1/3), `exterior-renovation-frontend.md` (2/3, written after backend Task 12), `exterior-renovation-deploy.md` (3/3). Design direction: `docs/design/direction.md`. Kept as the phase overview.

**Spec**: .planning/specs/exterior-renovation.md
**Epic**: none
**Created**: 2026-10-31
**Status**: draft
**Stack**: greenfield — Django 5 + DRF (Python 3.12) / React 18 + Vite (Node 22)

## Deviations from spec (tooling only)

| Spec said | Plan uses | Why |
|-----------|-----------|-----|
| WeasyPrint | **ReportLab** (platypus) | WeasyPrint needs GTK on Windows dev box; ReportLab is pure wheels, works on Windows + e2-micro |
| OpenCV blur check | **Pillow** `FIND_EDGES` + `ImageStat` variance | avoids ~50 MB dep for one metric |

---

## Architecture

Django layering (mirrors Controller → Manager → Repository/Service):

```
views.py (thin: parse, validate, call manager, serialize)
   ↓
managers/*.py (business logic, DB writes via ORM)
   ↓                    ↓
models.py (ORM)      ai.py (Vertex/Gemini service — external calls only, no DB)
                     estimation.py (pure functions — no DB, no IO)
```

### Components

| Component | Type | Purpose |
|-----------|------|---------|
| `models.py` | ORM | Project, Photo, Component, Design, RateCache, RateOverride (UUID pk, soft delete) |
| `estimation.py` | Pure logic | shoelace area, wall-net, pillar/railing rules, quantities, costs |
| `ai.py` | Service | Gemini calls: `check_photo`, `detect_structure`, `parse_text`, `recommend`, `search_rates`, `render` |
| `managers/photos.py` | Manager | upload, Pillow quality gate + AI gate, set primary |
| `managers/structure.py` | Manager | detect → quads, save edits, scale calibration |
| `managers/designs.py` | Manager | text/guided/manual → DesignSpec, validate vs catalog, render w/ cap + hash cache |
| `managers/rates.py` | Manager | priority chain override → cache → web → tier fallback |
| `managers/estimates.py` | Manager | assemble areas + spec + rates → estimate dict |
| `managers/report.py` | Manager | ReportLab PDF |
| `views.py` / `urls.py` | API | 18 endpoints from spec |
| `data/catalog.json`, `data/cities.json` | Seed | materials w/ base INR rates; ~100 cities w/ tier |
| `src/api.js` | FE client | axios, all endpoints |
| `src/steps/*` | FE pages | Upload, Detect, Design, Visualize, Estimate, Report |
| `src/components/*` | FE comps | Stepper, RegionCanvas, CompareSlider, RateCell, CitySelect |

### File locations

| File | Location |
|------|----------|
| Django project | `backend/config/{settings,urls,wsgi}.py` |
| App | `backend/core/{models,views,urls,ai,estimation}.py` |
| Managers | `backend/core/managers/{photos,structure,designs,rates,estimates,report}.py` |
| Seed | `backend/core/data/{catalog,cities}.json` |
| Tests | `backend/core/tests/test_{estimation,rates,designs,api}.py` |
| Fixtures | `backend/core/tests/fixtures/house.jpg` |
| Frontend | `frontend/src/{main.jsx,App.jsx,api.js,styles.css}` |
| Steps | `frontend/src/steps/{Upload,Detect,Design,Visualize,Estimate,Report}.jsx` |
| Components | `frontend/src/components/{Stepper,RegionCanvas,CompareSlider,RateCell,CitySelect}.jsx` |
| Deploy | `deploy/{setup_vm.sh,gunicorn.service,cloudflared.service}`, `frontend/.env.production` |
| Docs | `README.md`, `docs/{architecture,estimation,limitations}.md` |

### Files to change

None — greenfield.

---

## Tasks

### Phase 0: Spike (de-risk AI) — ~1 h

| # | Task | Files | Test |
|---|------|-------|------|
| 0.1 | Script: grounded search + JSON on `gemini-3.5-flash`; detection boxes on a real house photo; one render with geometry-preserve prompt | `scratchpad/spike.py` (not committed) | eyeball output; record whether search + `response_schema` combine |

### Phase 1: Backend foundation — ~2 h

| # | Task | Files | Test |
|---|------|-------|------|
| 1 | Django project + DRF + CORS + media + `.env` (project id, location, models) | `backend/config/settings.py`, `urls.py`, `requirements.txt` | `manage.py check` |
| 2 | Models + migration | `core/models.py`, `core/migrations/0001_initial.py` | `test_api.py::test_models_soft_delete` |
| 3 | Seed data | `core/data/catalog.json`, `core/data/cities.json` | `test_estimation.py::test_catalog_schema` |

### Phase 2: Estimation engine (TDD, pure) — ~2 h — parallel with Phase 3

| # | Task | Files | Test (write first) |
|---|------|-------|------|
| 4 | `area_sqft(quad, px_per_ft)`, `contains(wall, opening)`, `wall_net` | `core/estimation.py`, `tests/test_estimation.py` | known rect → exact sqft; degenerate → 0; window inside subtracted, outside not |
| 5 | Per-type measure (pillar ×4, railing rft) + quantities (paint L, tiles ⌈⌉, cladding, panels, railing) | same 2 | each unit w/ wastage; tiles round up |
| 6 | `estimate(components, spec, rates, px_per_ft)` → lines + totals + assumptions; resolve `component:` over `type:` | same 2 | grand total = Σ lines; override precedence; keep_unchanged excluded; no-scale flag |

### Phase 3: AI service — ~2 h — parallel with Phase 2

| # | Task | Files | Test |
|---|------|-------|------|
| 7 | `ai.py` client (google-genai, Vertex, global) + `check_photo`, `detect_structure` (box_2d 0–1000 → px quads) | `core/ai.py` | mocked: box conversion correct |
| 8 | `parse_text`, `recommend` (structured JSON output, catalog ids constrained by enum) | `core/ai.py` | mocked: unknown material → mapped/flagged |
| 9 | `search_rates(state, city, items)` grounded; `render(image, spec)` returns PNG bytes | `core/ai.py` | mocked: JSON parse from text fallback |

### Phase 4: Managers — ~3 h (depends on 1–9)

| # | Task | Files | Test |
|---|------|-------|------|
| 10 | Photos: Pillow gate (≥800 px short side, edge variance) + AI gate, set primary | `managers/photos.py` | tiny / blank image rejected w/ tips |
| 11 | Structure: detect, save edits, scale (`user` / `default` 7 ft door → 10 ft floor) | `managers/structure.py` | scale from door quad; default when none |
| 12 | Rates chain + 30-day cache + 0.3×–3× bounds + tier fallback + overrides | `managers/rates.py`, `tests/test_rates.py` | out-of-bounds → fallback; stale cache refetch; override wins; AI error → fallback |
| 13 | Designs: from-text, recommend (rule shortlist by climate/maintenance/budget tags → AI rationale), save, validate spec; render w/ hash cache + cap 8 → 429 | `managers/designs.py`, `tests/test_designs.py` | invalid material rejected; hash hit skips AI; 9th render → 429 |
| 14 | Estimates + PDF report | `managers/estimates.py`, `managers/report.py` | PDF bytes start `%PDF` |

### Phase 5: API — ~1.5 h (depends on Phase 4)

| # | Task | Files | Test |
|---|------|-------|------|
| 15 | Views + urls for all 18 endpoints; error shape `{error:{code,message,details}}` | `core/views.py`, `core/urls.py` | — |
| 16 | API smoke test (AI mocked): create → upload → detect → save design → estimate → report | `tests/test_api.py` | full flow 200s; bad id → 404; bad body → 400 |

**── Integration point: backend contract frozen ──**

### Phase 6: Frontend — ~6 h (depends on Phase 5 contract; can start 17–18 against spec earlier)

| # | Task | Files | Test |
|---|------|-------|------|
| 17 | Vite scaffold, axios client, project-by-URL (`?p=<uuid>`), stepper shell | `main.jsx`, `App.jsx`, `api.js` | build |
| 18 | Design tokens + base styles (light/dark, 375 px) | `styles.css`, `Stepper.jsx` | build |
| 19 | Upload step + CitySelect | `steps/Upload.jsx`, `components/CitySelect.jsx` | manual: reject tips show |
| 20 | Detect step: react-konva quads (drag corners, type, delete, add) + scale card | `steps/Detect.jsx`, `components/RegionCanvas.jsx` | manual: edit persists after reload |
| 21 | Design step: Describe / Help me choose / Manual tabs, design cards | `steps/Design.jsx` | manual: all 3 modes produce card |
| 22 | Visualize: render, before/after slider, design switcher | `steps/Visualize.jsx`, `components/CompareSlider.jsx` | manual |
| 23 | Estimate: table, badges, inline rate edit → recalc | `steps/Estimate.jsx`, `components/RateCell.jsx` | manual: edit rate → total changes |
| 24 | Report: download PDF, copy link; loading/empty/error states pass | `steps/Report.jsx` | `npm run build` clean |

### Phase 7: Deploy — ~2 h

| # | Task | Files | Test |
|---|------|-------|------|
| 25 | e2-micro (us-central1), service account w/ `roles/aiplatform.user`, swap 1 GB, gunicorn systemd | `deploy/setup_vm.sh`, `deploy/gunicorn.service` | `curl /api/catalog` on VM |
| 26 | Cloudflare Tunnel systemd → HTTPS URL; CORS allow Pages origin | `deploy/cloudflared.service`, `settings.py` | curl HTTPS URL |
| 27 | Cloudflare Pages deploy w/ `VITE_API_URL` | `frontend/.env.production` | live E2E with 2 real photos |

### Phase 8: Docs & submission — ~1.5 h

| # | Task | Files |
|---|------|-------|
| 28 | Architecture + workflow diagram, estimation method, limitations, run locally | `README.md`, `docs/architecture.md`, `docs/estimation.md`, `docs/limitations.md` |
| 29 | Submission email draft (live link, notes) | `docs/submission.md` |

**Total ≈ 21 h** → fits 48 h with buffer for render/detection prompt tuning.

---

## Parallel vs sequential

| Parallel group | Tasks | Why |
|----------------|-------|-----|
| A | 4–6 ∥ 7–9 | estimation pure, AI service independent |
| B | 17–18 ∥ Phase 4 | FE shell only needs spec contract |
| C | 28 drafting ∥ Phase 7 | docs from spec |

| Sequential | Depends on | Why |
|------------|-----------|-----|
| 0.1 | — | decides grounded-search JSON strategy for task 9 |
| 10–14 | 1–9 | use models, engine, AI |
| 15–16 | 10–14 | thin views over managers |
| 19–24 | 15 | live API |
| 27 | 25–26, 24 | needs HTTPS backend + built FE |

---

## Testing plan → spec trace

| Test | Spec item |
|------|-----------|
| models soft delete, UUID | Data model |
| area / wall-net / degenerate quad | M9, edge 11 |
| quantities incl. wastage, tiles round-up | M10 |
| estimate totals, override precedence, keep_unchanged | M12, M7 |
| no-scale default flag | M4, edge 3 |
| rate bounds / stale cache / AI error fallback / override | M11, edges 6, 7 |
| unknown material, missing component target | M6, edges 4, 5 |
| render hash cache + cap 429 | M8, edge 9 |
| photo gate rejects tiny/blank | M1, edge 1 |
| detect returns empty → manual add allowed (API) | M3, edge 2 |
| Vertex timeout → retry once → error (mocked) | edge 10 |
| API full flow + 404/400 | M14, all |
| PDF `%PDF` | M13 |
| FE build + manual E2E on live link | M1–M14, UI |

Edge 8 (render drift) & 12 (last-write-wins) → documented in limitations, not tested.

---

## Gate 2

- [x] Follows layered pattern (views → managers → ORM / ai service / pure engine)
- [x] Each layer only calls the one below; `ai.py` has no DB; `estimation.py` has no IO
- [x] All new files + locations listed; no existing files (greenfield)
- [x] Tasks ≤ 3 files, ordered, dependencies + parallel groups marked
- [x] Data, logic, API, UI tests planned; spec edge cases traced
