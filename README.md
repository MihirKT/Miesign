# Miesign

AI exterior renovation planner and INR cost estimator: upload one photo of a house, pick materials and colours, see a preview, and get an itemised estimate.

Designed and built by Mihir Kapildev Tiwari.

Live: https://miesign.pages.dev · Submission notes: https://miesign.pages.dev/submission/

## What it does

1. **Photo.** Upload a house photo. Local checks (size, blur) run first, then Gemini confirms it is a house with the front visible. Choose the city for local rates.
2. **Parts.** Gemini detects walls, windows, doors, balconies, pillars, parapets, gates, roof edges and railings as boxes. Drag, retype, add or delete them. Optionally enter one real height to fix the scale.
3. **Design.** Describe the look in words, answer four guided questions for three suggestions, or pick materials and colours by hand.
4. **Preview.** Gemini edits the photo with the chosen materials. Compare with the original on a slider. Eight previews per project.
5. **Estimate.** Areas, quantities with wastage, and costs per category, using city rates. Any rate can be overridden.
6. **Report.** Download a PDF with the photos, materials, measurements and cost breakdown.

## Tech stack

- Backend: Python, Django 5, Django REST Framework, SQLite, Pillow, ReportLab.
- AI: Gemini on Google Vertex AI through `google-genai` (`gemini-3.5-flash` for text and vision, `gemini-3.1-flash-image` for renders).
- Frontend: React 18, TypeScript, Vite, Konva (part editor), Vitest.

## Repository structure

```
backend/
  config/            Django settings, root URLs, WSGI
  core/
    models.py        6 models with soft delete
    views.py         thin HTTP layer
    urls.py          the 18 endpoints
    managers/        business logic (projects, photos, structure, rates, designs, estimates, report)
    ai.py            all Gemini calls
    estimation.py    pure geometry, quantity and cost maths
    catalog.py       loads data/catalog.json (12 materials) and data/cities.json
    errors.py        AppError and the JSON error shape
    serializers.py   model to JSON dicts
    tests/           pytest suite
  scripts/
    smoke_ai.py          live end-to-end run against Vertex
    requirement_check.py live colour-accuracy check on sample photos
  .env.example       every backend setting with its default
frontend/
  src/
    App.tsx          app shell and step routing
    steps/           one component per step (Photo, Parts, Design, Preview, Estimate, Report)
    components/      canvas editor, compare slider, rate cell, city select, step rail
    lib/             API client, types, formatting, quad geometry, palette
    tokens.css       design tokens
    styles.css       styles (reference tokens only)
  .env.example       VITE_API_URL
docs/                architecture, estimation, limitations, design direction
.planning/           spec and implementation plans
```

## Run locally

Backend (from `backend/`):

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash; use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver         # http://127.0.0.1:8000
```

AI calls use Application Default Credentials on Vertex AI:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project <your-gcp-project>
```

Set `GCP_PROJECT` to the same project (see below).

Frontend (from `frontend/`):

```bash
npm install
npm run dev                        # http://localhost:5173, proxies /api and /media to :8000
```

## Deploy

One Google Cloud e2-micro VM (free tier, us-central1) with a service account that has `roles/aiplatform.user`, so Vertex needs no key file. Caddy serves `frontend/dist` over HTTPS (Let's Encrypt via sslip.io, no domain needed) and proxies `/api` and `/media` to gunicorn. Copy `miesign.tgz` (`git archive HEAD backend`), `dist.tgz` and `settings.py` to `/tmp` on the VM, then run `sudo bash deploy/setup.sh <host>`.

The public URL is Cloudflare Pages: `cd frontend && npm run build && npx wrangler pages deploy dist --project-name miesign --branch main`. `frontend/functions/api/[[path]].js` forwards `/api/*` to the VM so the app and API share the `miesign.pages.dev` origin. Before deploying, copy `docs/submission` into `dist/submission` (with the HTML renamed to `index.html`) to publish the submission notes.

## Environment variables

All optional. See [`backend/.env.example`](backend/.env.example) for every backend setting with its default and [`frontend/.env.example`](frontend/.env.example) for `VITE_API_URL`.

## Tests

```bash
cd backend && pytest               # 100 tests, AI layer stubbed
cd frontend && npx vitest run      # 21 tests
```

## Live checks (cost Gemini calls)

From `backend/` with the venv active and ADC set up:

```bash
python scripts/smoke_ai.py scripts/samples/house1.png Maharashtra Pune   # whole pipeline once
python scripts/requirement_check.py                                      # 3 photos: colour asked vs colour rendered
```

## Docs

- [Architecture](docs/architecture.md): diagram, layers, data model, API, workflow.
- [Estimation](docs/estimation.md): how areas and costs are computed, with a worked example.
- [Limitations](docs/limitations.md): what the numbers and the preview can and cannot be trusted for.
- [Design direction](docs/design/direction.md): visual system choices.
- [Spec](.planning/specs/exterior-renovation.md) and [plans](.planning/plans/).

## Sample photos

`backend/scripts/samples/ATTRIBUTION.txt` lists the Wikimedia Commons photos with author and licence. The `user-house-*.jpg` files are the author's own test images. The samples folder is git-ignored, so it exists only on the author's machine.
