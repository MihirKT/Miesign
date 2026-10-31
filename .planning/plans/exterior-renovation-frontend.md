# Exterior Renovation — Frontend Implementation Plan (2 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A React wizard (`01 Photo · 02 Parts · 03 Design · 04 Preview · 05 Estimate · 06 Report`) on top of the frozen backend API, so a homeowner can upload a photo, fix detected parts, pick materials three ways, see the redesign, edit INR rates and download the PDF.

**Architecture:** One page, no router; the project lives in the URL as `?p=<uuid>`. `src/lib/*` holds pure, unit-tested logic (case conversion, API client, formatting, step gating, quad geometry, cost grouping). `src/steps/*` are the six screens; `src/components/*` are shared widgets. `App.tsx` owns the `Project` state and passes it down. Styling is plain CSS on Hallmark tokens (`docs/design/direction.md`).

**Tech Stack:** React 18 · TypeScript 5.6 · Vite 5 · Vitest 2 · Konva + react-konva (region editor) · native `fetch` · plain CSS.

**Depends on:** backend plan 1 (API frozen at commit `b4fd5b1`). **Next:** plan 3 (deploy + docs).

## Global Constraints

- API base: `import.meta.env.VITE_API_URL` (empty in dev; Vite proxies `/api` and `/media` to `http://127.0.0.1:8000`).
- Wire format is `snake_case`; TS code is `camelCase`; convert in `src/lib/api.ts` only (`keysToSnake` on bodies, `keysToCamel` on responses). Query-param names are written in snake_case by hand.
- Errors: show `error.message` from `{"error": {code, message, status, details}}`; never show raw fetch/HTTP text; fallback "Something went wrong. Try again."
- Design tokens are binding: every colour and font comes from `var(--…)` in `src/tokens.css`. No raw hex/oklch/rgb in CSS or TSX styling. (User-chosen paint colours are data, not styling.)
- Hallmark rules: headings roman (never italic); stage label stacked above heading (`02 · PARTS`), never hanging left; `html, body { overflow-x: clip }`; buttons/nav/CTAs never wrap to two lines; image grid tracks `minmax(0, 1fr)`; headings `overflow-wrap: anywhere; min-width: 0`; `:focus-visible` ring always; `prefers-reduced-motion` honoured; ≤ 3 motion primitives (step fade, total count-up, part highlight).
- Touch targets ≥ 44 px on mobile; layout works at 320 / 375 / 414 / 768 / 1440 px with no horizontal page scroll (a table may scroll inside its own box).
- Money: `₹` with Indian grouping via `Intl.NumberFormat('en-IN')`.
- No invented numbers or testimonials; all money comes from the API.
- Tests: Vitest for everything in `src/lib/`. Screens are verified by `npm run build` (strict TS, no unused code) per task and by the browser walkthrough in Task 12.
- Commit trailer on every commit: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

All commands run from `C:\Users\mihir\Desktop\E2M\frontend` unless stated. Use Git Bash. Branch: `feature/exterior-renovation-frontend` (created in Task 1 from the backend branch tip).

---

## File map

| File | Responsibility |
|---|---|
| `frontend/package.json`, `vite.config.ts`, `tsconfig.json`, `index.html` | toolchain, fonts |
| `frontend/src/main.tsx` | mount |
| `frontend/src/tokens.css` | Hallmark tokens (stamped) |
| `frontend/src/styles.css` | all component styles |
| `frontend/src/lib/types.ts` | API types (camelCase) |
| `frontend/src/lib/case.ts` | key case conversion |
| `frontend/src/lib/format.ts` | ₹, numbers, labels, dates |
| `frontend/src/lib/steps.ts` | step list, gating, resume |
| `frontend/src/lib/quad.ts` | region geometry for the editor |
| `frontend/src/lib/estimate.ts` | group cost lines by category |
| `frontend/src/lib/api.ts` | fetch client + ApiError |
| `frontend/src/lib/hooks.ts` | `useElapsed`, `useCountUp` |
| `frontend/src/App.tsx` | project state, step switching |
| `frontend/src/components/StepRail.tsx` | N3 side rail + mobile step bar |
| `frontend/src/components/CitySelect.tsx` | state → city picker |
| `frontend/src/components/RegionCanvas.tsx` | Konva quad editor |
| `frontend/src/components/CompareSlider.tsx` | before/after |
| `frontend/src/components/RateCell.tsx` | editable rate |
| `frontend/src/steps/{PhotoStep,PartsStep,DesignStep,PreviewStep,EstimateStep,ReportStep}.tsx` | screens |

---

### Task 1: Scaffold Vite + TS + Vitest + tokens

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx` (placeholder), `frontend/src/tokens.css`, `frontend/src/styles.css`, `frontend/src/vite-env.d.ts`

**Interfaces:**
- Produces: CSS tokens and classes used by every later task: `.app .rail .wordmark .step-link .num .mobile-bar .step-jump .progress main .stage-head .label .lede .workspace .panel .stack .row .btn .btn-primary .btn-small .field .notice(.error|.ok|.warn) .mono .badge(.web|.override) .dropzone .thumbs .thumb .part-list .part-row .swatch .canvas-wrap .tabs .tab .chips .chip .design-list .design .compare .after .divider .compare-range .table-scroll .cost-table .num .subtotal .rate-input .total-bar .amount .footer .sr-only .fade-in`.

- [ ] **Step 1: Branch**

Run from `C:\Users\mihir\Desktop\E2M`:
```bash
git checkout -b feature/exterior-renovation-frontend
```

- [ ] **Step 2: Toolchain files**

`frontend/package.json`:
```json
{
  "name": "facade-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "konva": "^9.3.16",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-konva": "^18.2.10"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "~5.6.3",
    "vite": "^5.4.11",
    "vitest": "^2.1.8"
  }
}
```

`frontend/vite.config.ts`:
```ts
/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const BACKEND = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': BACKEND, '/media': BACKEND } },
  test: { environment: 'node' },
})
```

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "noEmit": true
  },
  "include": ["src", "vite.config.ts"]
}
```

`frontend/src/vite-env.d.ts`:
```ts
/// <reference types="vite/client" />
```

`frontend/index.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="See your house redesigned and get a material and cost estimate before construction begins." />
    <title>Facade · renovation planner</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      rel="stylesheet"
      href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Newsreader:opsz,wght@6..72,500;6..72,600&display=swap"
    />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`frontend/src/main.tsx`:
```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './tokens.css'
import './styles.css'

const root = document.getElementById('root')
if (root) {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}
```

`frontend/src/App.tsx` (placeholder; replaced in Task 5):
```tsx
export default function App() {
  return <main><h1>Facade</h1></main>
}
```

- [ ] **Step 3: Tokens**

`frontend/src/tokens.css`:
```css
/* Hallmark · macrostructure: Narrative Workflow · nav: N3 Side-rail · footer: Ft2 Inline
 * theme: Almanac · tone: utilitarian · anchor hue: 38 (brick) · enrichment: none
 */
:root {
  --color-paper: oklch(97.5% 0.006 240);
  --color-paper-2: oklch(94.5% 0.008 240);
  --color-paper-3: oklch(91% 0.01 240);
  --color-rule: oklch(86% 0.01 240);
  --color-ink: oklch(24% 0.02 250);
  --color-ink-2: oklch(40% 0.018 250);
  --color-ink-3: oklch(50% 0.014 250);

  --color-accent: oklch(52% 0.15 38);
  --color-accent-hover: oklch(46% 0.15 38);
  --color-accent-ink: oklch(98% 0.01 60);
  --color-accent-wash: oklch(94% 0.03 45);

  --color-ok: oklch(50% 0.12 150);
  --color-warn: oklch(58% 0.13 75);
  --color-error: oklch(50% 0.17 25);
  --color-focus: oklch(52% 0.17 250);

  --region-wall: oklch(62% 0.14 38);
  --region-window: oklch(62% 0.14 230);
  --region-door: oklch(62% 0.14 280);
  --region-balcony: oklch(62% 0.14 150);
  --region-pillar: oklch(62% 0.14 85);
  --region-parapet: oklch(62% 0.14 330);
  --region-gate: oklch(62% 0.14 190);
  --region-roof_edge: oklch(62% 0.14 0);
  --region-railing: oklch(62% 0.14 120);

  --font-display: "Newsreader", ui-serif, Georgia, serif;
  --font-body: "IBM Plex Sans", ui-sans-serif, sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, monospace;
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.375rem;
  --text-2xl: 1.75rem;
  --text-3xl: 2.25rem;

  --space-2xs: 4px;
  --space-xs: 8px;
  --space-sm: 12px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;
  --space-3xl: 64px;

  --radius-sm: 4px;
  --radius-md: 6px;
  --rule-hair: 1px solid var(--color-rule);
  --rule-thick: 2px solid var(--color-ink);

  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in: cubic-bezier(0.7, 0, 0.84, 0);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --dur-fast: 120ms;
  --dur-base: 200ms;
  --dur-slow: 320ms;
}
```

- [ ] **Step 4: Styles**

`frontend/src/styles.css`:
```css
/* Hallmark · macrostructure: Narrative Workflow · theme: Almanac — styles reference tokens.css only */
*, *::before, *::after { box-sizing: border-box; }
html, body { overflow-x: clip; }
body {
  margin: 0;
  background: var(--color-paper);
  color: var(--color-ink);
  font-family: var(--font-body);
  font-size: var(--text-base);
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
h1, h2, h3 {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 600;
  font-style: normal;
  line-height: 1.15;
  overflow-wrap: anywhere;
  min-width: 0;
}
h1 { font-size: var(--text-3xl); }
h2 { font-size: var(--text-xl); }
h3 { font-size: var(--text-lg); }
p { margin: 0; }
img { display: block; max-width: 100%; }
a { color: var(--color-accent); }
button, input, select, textarea { font: inherit; color: inherit; }
:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.sr-only {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}

/* layout */
.app { display: grid; grid-template-columns: 220px minmax(0, 1fr); min-height: 100dvh; }
.rail {
  position: sticky; top: 0; height: 100dvh;
  display: flex; flex-direction: column; gap: var(--space-xl);
  padding: var(--space-xl) var(--space-lg);
  border-right: var(--rule-hair);
}
.wordmark { font-family: var(--font-display); font-weight: 600; font-size: var(--text-xl); }
.rail ol { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--space-2xs); }
.step-link {
  display: flex; align-items: baseline; gap: var(--space-sm); width: 100%;
  padding: var(--space-xs) var(--space-sm); border: 0; border-left: 2px solid transparent;
  background: none; color: var(--color-ink-2); text-align: left; white-space: nowrap; cursor: pointer;
  transition: background-color var(--dur-fast) var(--ease-out);
}
.step-link .num { font-family: var(--font-mono); font-size: var(--text-xs); }
.step-link:hover:not(:disabled) { background: var(--color-paper-2); }
.step-link[aria-current="step"] { color: var(--color-ink); font-weight: 600; border-left-color: var(--color-accent); }
.step-link:disabled { color: var(--color-ink-3); cursor: not-allowed; }
.mobile-bar { display: none; }
main { width: 100%; max-width: 1200px; padding: var(--space-2xl) var(--space-xl) var(--space-3xl); }
.stage-head { display: grid; gap: var(--space-xs); margin-bottom: var(--space-xl); }
.label {
  font-family: var(--font-mono); font-size: var(--text-xs); letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--color-ink-2);
}
.lede { color: var(--color-ink-2); max-width: 60ch; }
.workspace { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: var(--space-xl); align-items: start; }
.panel { display: grid; gap: var(--space-md); padding-top: var(--space-md); border-top: var(--rule-thick); }
.stack { display: grid; gap: var(--space-md); }
.row { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-sm); }
.fade-in { animation: fade-in var(--dur-base) var(--ease-out); }
@keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }

/* controls */
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: var(--space-xs);
  min-height: 44px; padding: 0 var(--space-lg);
  border: 1px solid var(--color-ink-2); border-radius: var(--radius-sm);
  background: transparent; font-weight: 500; white-space: nowrap; cursor: pointer; text-decoration: none;
  color: var(--color-ink);
  transition: background-color var(--dur-fast) var(--ease-out), transform var(--dur-fast) var(--ease-out);
}
.btn:hover:not(:disabled) { background: var(--color-paper-2); }
.btn:active:not(:disabled) { transform: translateY(1px); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn[aria-busy="true"] { cursor: progress; }
.btn-primary { background: var(--color-accent); border-color: var(--color-accent); color: var(--color-accent-ink); }
.btn-primary:hover:not(:disabled) { background: var(--color-accent-hover); }
.btn-small { min-height: 36px; padding: 0 var(--space-sm); font-size: var(--text-sm); }
.field { display: grid; gap: var(--space-2xs); }
.field > label, .field > .field-label { font-size: var(--text-sm); font-weight: 500; }
input[type="text"], input[type="number"], select, textarea {
  width: 100%; min-height: 44px; padding: var(--space-xs) var(--space-sm);
  border: 1px solid var(--color-rule); border-radius: var(--radius-sm); background: var(--color-paper);
}
input:hover, select:hover, textarea:hover { border-color: var(--color-ink-3); }
[aria-invalid="true"] { border-color: var(--color-error); }
textarea { min-height: 112px; resize: vertical; }
.step-jump { width: auto; min-height: 40px; }

/* feedback */
.notice {
  padding: var(--space-sm) var(--space-md); border-left: 2px solid var(--color-ink-3);
  background: var(--color-paper-2); font-size: var(--text-sm);
}
.notice.error { border-left-color: var(--color-error); }
.notice.ok { border-left-color: var(--color-ok); }
.notice.warn { border-left-color: var(--color-warn); }
.notice ul { margin: var(--space-2xs) 0 0; padding-left: 1.1em; }
.mono { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.badge {
  font-family: var(--font-mono); font-size: var(--text-xs); letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--color-ink-3); white-space: nowrap;
}
.badge.web { color: var(--color-ok); }
.badge.override { color: var(--color-accent); }

/* 01 photo */
.dropzone {
  display: grid; place-items: center; gap: var(--space-sm); min-height: 240px;
  padding: var(--space-xl); border: 1px dashed var(--color-ink-3); border-radius: var(--radius-md);
  text-align: center; cursor: pointer; background: var(--color-paper);
}
.dropzone:focus-within { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.dropzone[data-over="true"] { background: var(--color-accent-wash); border-color: var(--color-accent); }
.thumbs { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(min(160px, 100%), 1fr)); gap: var(--space-md); }
.thumb { display: grid; gap: var(--space-xs); padding: var(--space-xs); border: var(--rule-hair); border-radius: var(--radius-sm); }
.thumb[data-primary="true"] { border-color: var(--color-accent); }
.thumb img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; }

/* 02 parts */
.canvas-wrap { border: var(--rule-hair); background: var(--color-paper-2); touch-action: none; }
.part-list { list-style: none; margin: 0; padding: 0; display: grid; max-height: 420px; overflow-y: auto; }
.part-row {
  display: grid; grid-template-columns: 12px minmax(0, 1fr) auto; align-items: center; gap: var(--space-sm);
  padding: var(--space-xs) var(--space-2xs); border-bottom: var(--rule-hair);
}
.part-row[aria-selected="true"] { background: var(--color-accent-wash); }
.swatch { width: 12px; height: 12px; border-radius: 2px; }

/* 03 design */
.tabs { display: flex; gap: var(--space-2xs); border-bottom: var(--rule-hair); overflow-x: auto; }
.tab {
  min-height: 44px; padding: var(--space-sm) var(--space-md); border: 0; border-bottom: 2px solid transparent;
  background: none; white-space: nowrap; cursor: pointer;
}
.tab[aria-selected="true"] { border-bottom-color: var(--color-accent); font-weight: 600; }
.chips { display: flex; flex-wrap: wrap; gap: var(--space-xs); }
.chip {
  min-height: 40px; padding: 0 var(--space-md); border: 1px solid var(--color-rule); border-radius: 999px;
  background: var(--color-paper); white-space: nowrap; cursor: pointer;
}
.chip:hover { border-color: var(--color-ink-3); }
.chip[aria-pressed="true"] { border-color: var(--color-ink); background: var(--color-ink); color: var(--color-paper); }
.design-list { display: grid; gap: var(--space-md); }
.design { display: grid; gap: var(--space-xs); padding-top: var(--space-md); border-top: var(--rule-hair); }
.design[data-active="true"] h3 { color: var(--color-accent); }

/* 04 preview */
.compare { position: relative; --pos: 50%; overflow: hidden; border: var(--rule-hair); }
.compare img { width: 100%; }
.compare .after { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; clip-path: inset(0 0 0 var(--pos)); }
.compare .divider {
  position: absolute; top: 0; bottom: 0; left: var(--pos); width: 2px;
  background: var(--color-paper); box-shadow: 0 0 0 1px var(--color-ink-3); pointer-events: none;
}
.compare-range { width: 100%; accent-color: var(--color-accent); }

/* 05 estimate */
.table-scroll { overflow-x: auto; }
.cost-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.cost-table th { padding: var(--space-xs); border-bottom: var(--rule-thick); color: var(--color-ink-2); font-weight: 500; text-align: left; white-space: nowrap; }
.cost-table td { padding: var(--space-xs); border-bottom: var(--rule-hair); vertical-align: top; }
.cost-table .num { text-align: right; font-family: var(--font-mono); font-variant-numeric: tabular-nums; white-space: nowrap; }
.cost-table .subtotal td { font-weight: 600; border-bottom: var(--rule-thick); }
.rate-input { width: 8ch; min-height: 36px; text-align: right; font-family: var(--font-mono); }
.total-bar {
  position: sticky; bottom: 0; display: flex; justify-content: space-between; align-items: baseline; gap: var(--space-md);
  padding: var(--space-md) 0; border-top: var(--rule-thick); background: var(--color-paper);
}
.total-bar .amount { font-family: var(--font-mono); font-size: var(--text-2xl); font-weight: 500; white-space: nowrap; }
.footer { margin-top: var(--space-3xl); padding-top: var(--space-md); border-top: var(--rule-hair); font-size: var(--text-xs); color: var(--color-ink-3); }

@media (max-width: 1023px) {
  .workspace { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 767px) {
  .app { grid-template-columns: minmax(0, 1fr); }
  .rail { display: none; }
  .mobile-bar { display: block; position: sticky; top: 0; z-index: 2; background: var(--color-paper); border-bottom: var(--rule-hair); }
  .mobile-bar .inner { display: flex; align-items: center; justify-content: space-between; gap: var(--space-sm); padding: var(--space-sm) var(--space-md); }
  .mobile-bar .progress { height: 2px; width: calc(var(--done) * 100%); background: var(--color-accent); }
  main { padding: var(--space-lg) var(--space-md) var(--space-3xl); }
  h1 { font-size: var(--text-2xl); }
  .btn-small, .rate-input { min-height: 44px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 1ms !important; transition-duration: 1ms !important; }
}
```

- [ ] **Step 5: Install + build**

Run: `npm install && npm run build`
Expected: install succeeds; build prints `✓ built in …` with no TS errors.

- [ ] **Step 6: Commit**

```bash
cd .. && git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/tsconfig.json frontend/index.html frontend/src && git commit -m "chore: scaffold React frontend with Hallmark tokens

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Types, case conversion, formatting

**Files:**
- Create: `frontend/src/lib/types.ts`, `frontend/src/lib/case.ts`, `frontend/src/lib/format.ts`
- Test: `frontend/src/lib/case.test.ts`, `frontend/src/lib/format.test.ts`

**Interfaces:**
- Produces: all API types below; `keysToCamel<T>(v: unknown): T`, `keysToSnake(v: unknown): unknown`; `inr(n)`, `num(n)`, `typeLabel(t)`, `shortDate(iso)`.

- [ ] **Step 1: Types (no test; consumed everywhere)**

`frontend/src/lib/types.ts`:
```ts
export const COMPONENT_TYPES = [
  'wall', 'window', 'door', 'balcony', 'pillar', 'parapet', 'gate', 'roof_edge', 'railing',
] as const
export type ComponentType = (typeof COMPONENT_TYPES)[number]
export type Point = [number, number]
export type Quad = [Point, Point, Point, Point]

export interface Part {
  id?: string
  type: ComponentType
  quad: Quad
  floor: number
  source?: 'ai' | 'user'
  confidence?: number | null
}

export interface Photo {
  id: string
  url: string
  width: number
  height: number
  qualityOk: boolean
  issues: string[]
  tips: string[]
}

export interface Assignment {
  target: string
  materialId: string
  color: string | null
  finish: string
}

export interface DesignSpec {
  style: string
  palette: string[]
  assignments: Assignment[]
  keepUnchanged: ComponentType[]
}

export interface Design {
  id: string
  name: string
  mode: 'free_text' | 'guided' | 'manual'
  input: Record<string, unknown>
  spec: DesignSpec
  rationale: string
  warnings: string[]
  renderUrl: string | null
  createdAt: string
}

export interface Project {
  id: string
  name: string
  state: string
  city: string
  pxPerFt: number | null
  scaleSource: 'default' | 'user'
  primaryPhotoId: string | null
  renderCount: number
  renderCap: number
  photos: Photo[]
  components: Part[]
  designs: Design[]
}

export interface Material {
  id: string
  name: string
  category: string
  appliesTo: ComponentType[]
  rateUnit: 'sqft' | 'rft'
  qtyUnit: string
  wastagePct: number
  baseMaterialRate: number
  baseLaborRate: number
  durabilityYears: string
  maintenance: 'low' | 'medium' | 'high'
  budget: 'low' | 'mid' | 'high'
  climates: string[]
  styles: string[]
}

export interface RateRow {
  materialId: string
  rateUnit: 'sqft' | 'rft'
  materialRate: number
  laborRate: number
  source: 'web' | 'estimated' | 'override'
  sources: string[]
  fetchedAt: string | null
}

export interface EstimateLine {
  category: string
  materialId: string
  name: string
  targets: string[]
  measure: number
  rateUnit: 'sqft' | 'rft'
  quantity: number
  qtyUnit: string
  wastagePct: number
  materialRate: number
  laborRate: number
  rateSource: 'web' | 'estimated' | 'override'
  materialCost: number
  laborCost: number
  total: number
}

export interface Estimate {
  scale: { pxPerFt: number; source: 'default' | 'user' }
  lines: EstimateLine[]
  grandTotal: number
  assumptions: string[]
  warnings: string[]
  location: { state: string; city: string }
}

export interface StateEntry {
  name: string
  cities: { name: string; tier: number }[]
}

export interface Answers {
  budget: 'low' | 'mid' | 'high'
  climate: 'coastal' | 'heavy_rain' | 'hot_dry' | 'moderate'
  style: 'modern' | 'traditional' | 'minimal' | 'luxe'
  maintenance: 'low' | 'medium'
  colorMood: string
  keepUnchanged: ComponentType[]
}
```

- [ ] **Step 2: Write the failing tests**

`frontend/src/lib/case.test.ts`:
```ts
import { expect, it } from 'vitest'
import { keysToCamel, keysToSnake } from './case'

const SNAKE = {
  project_id: 'p',
  quad: [[1, 2], [3, 4]],
  designs: [{
    render_url: null,
    spec: { keep_unchanged: ['roof_edge'], assignments: [{ material_id: 'x', target: 'type:roof_edge' }] },
  }],
}
const CAMEL = {
  projectId: 'p',
  quad: [[1, 2], [3, 4]],
  designs: [{
    renderUrl: null,
    spec: { keepUnchanged: ['roof_edge'], assignments: [{ materialId: 'x', target: 'type:roof_edge' }] },
  }],
}

it('converts nested keys both ways and leaves values alone', () => {
  expect(keysToCamel(SNAKE)).toEqual(CAMEL)
  expect(keysToSnake(CAMEL)).toEqual(SNAKE)
})

it('passes FormData and primitives through untouched', () => {
  const form = new FormData()
  expect(keysToSnake(form)).toBe(form)
  expect(keysToCamel(5)).toBe(5)
  expect(keysToCamel(null)).toBeNull()
})
```

`frontend/src/lib/format.test.ts`:
```ts
import { expect, it } from 'vitest'
import { inr, num, shortDate, typeLabel } from './format'

it('formats rupees with Indian grouping and no paise', () => {
  expect(inr(184500)).toBe('₹1,84,500')
  expect(inr(0)).toBe('₹0')
  expect(inr(12345678)).toBe('₹1,23,45,678')
})

it('formats measures to one decimal', () => {
  expect(num(12.345)).toBe('12.3')
  expect(num(1000)).toBe('1,000')
})

it('labels part types', () => {
  expect(typeLabel('roof_edge')).toBe('Roof edge')
  expect(typeLabel('wall')).toBe('Wall')
})

it('formats a short date', () => {
  expect(shortDate('2026-10-31T12:00:00Z')).toBe('31 Oct')
  expect(shortDate(null)).toBe('')
})
```

- [ ] **Step 3: Run to verify they fail**

Run: `npx vitest run src/lib`
Expected: FAIL — `Failed to resolve import "./case"` / `"./format"`.

- [ ] **Step 4: Implement**

`frontend/src/lib/case.ts`:
```ts
const toCamel = (key: string) => key.replace(/_([a-z0-9])/g, (_, c: string) => c.toUpperCase())
const toSnake = (key: string) => key.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`)

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && Object.getPrototypeOf(value) === Object.prototype
}

function convert(value: unknown, rename: (key: string) => string): unknown {
  if (Array.isArray(value)) return value.map((v) => convert(v, rename))
  if (isPlainObject(value)) {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [rename(k), convert(v, rename)]))
  }
  return value
}

export function keysToCamel<T>(value: unknown): T {
  return convert(value, toCamel) as T
}

export function keysToSnake(value: unknown): unknown {
  return convert(value, toSnake)
}
```

`frontend/src/lib/format.ts`:
```ts
const RUPEES = new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR', minimumFractionDigits: 0, maximumFractionDigits: 0,
})
const MEASURE = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 1 })
const SHORT_DATE = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' })

export const inr = (amount: number) => RUPEES.format(amount)
export const num = (value: number) => MEASURE.format(value)

export function typeLabel(type: string): string {
  const words = type.replace(/_/g, ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

export function shortDate(iso: string | null): string {
  return iso ? SHORT_DATE.format(new Date(iso)) : ''
}
```

- [ ] **Step 5: Run tests**

Run: `npx vitest run src/lib`
Expected: `6 passed`.

- [ ] **Step 6: Commit**

```bash
cd .. && git add frontend/src/lib && git commit -m "feat: add API types, case conversion and formatting

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Step gating, quad geometry, cost grouping

**Files:**
- Create: `frontend/src/lib/steps.ts`, `frontend/src/lib/quad.ts`, `frontend/src/lib/estimate.ts`
- Test: `frontend/src/lib/steps.test.ts`, `frontend/src/lib/quad.test.ts`, `frontend/src/lib/estimate.test.ts`

**Interfaces:**
- Consumes: `Project`, `Quad`, `Point`, `EstimateLine` (Task 2).
- Produces:
  - `STEPS: readonly {key, label}[]`, `type StepKey = 'photo'|'parts'|'design'|'preview'|'estimate'|'report'`, `unlockedSteps(p: Project | null): Set<StepKey>`, `resumeStep(p: Project): StepKey`
  - `rectQuad(x0, y0, x1, y1): Quad`, `clampPoint(p, w, h): Point`, `moveCorner(q, i, p, w, h): Quad`, `translateQuad(q, dx, dy, w, h): Quad`, `newPartQuad(w, h): Quad`
  - `groupByCategory(lines): CategoryGroup[]` with `CategoryGroup = {category, lines, materialCost, laborCost, total}`

- [ ] **Step 1: Write the failing tests**

`frontend/src/lib/steps.test.ts`:
```ts
import { expect, it } from 'vitest'
import type { Project } from './types'
import { resumeStep, unlockedSteps } from './steps'

const base: Project = {
  id: 'p', name: 'x', state: '', city: '', pxPerFt: null, scaleSource: 'default', primaryPhotoId: null,
  renderCount: 0, renderCap: 8, photos: [], components: [], designs: [],
}
const part = { type: 'wall' as const, quad: [[0, 0], [1, 0], [1, 1], [0, 1]] as Project['components'][number]['quad'], floor: 0 }

it('only photo is open before a usable photo', () => {
  expect([...unlockedSteps(null)]).toEqual(['photo'])
  expect([...unlockedSteps(base)]).toEqual(['photo'])
})

it('unlocks steps as the project fills in', () => {
  const withPhoto = { ...base, primaryPhotoId: 'ph' }
  expect(unlockedSteps(withPhoto).has('parts')).toBe(true)
  expect(unlockedSteps(withPhoto).has('design')).toBe(false)
  const withParts = { ...withPhoto, components: [part] }
  expect(unlockedSteps(withParts).has('design')).toBe(true)
  const withDesign = { ...withParts, designs: [{ id: 'd' } as Project['designs'][number]] }
  expect(unlockedSteps(withDesign)).toEqual(new Set(['photo', 'parts', 'design', 'preview', 'estimate', 'report']))
})

it('resumes at the furthest working step', () => {
  expect(resumeStep(base)).toBe('photo')
  expect(resumeStep({ ...base, primaryPhotoId: 'ph' })).toBe('parts')
  expect(resumeStep({ ...base, primaryPhotoId: 'ph', components: [part] })).toBe('design')
})
```

`frontend/src/lib/quad.test.ts`:
```ts
import { expect, it } from 'vitest'
import { clampPoint, moveCorner, newPartQuad, rectQuad, translateQuad } from './quad'

it('builds and clamps', () => {
  expect(rectQuad(1, 2, 3, 4)).toEqual([[1, 2], [3, 2], [3, 4], [1, 4]])
  expect(clampPoint([-5, 120], 100, 100)).toEqual([0, 100])
})

it('moves one corner inside the image', () => {
  const q = rectQuad(10, 10, 50, 50)
  expect(moveCorner(q, 2, [200, 60], 100, 100)).toEqual([[10, 10], [50, 10], [100, 60], [10, 50]])
})

it('translates the whole quad but keeps it inside', () => {
  const q = rectQuad(10, 10, 50, 50)
  expect(translateQuad(q, 5, -3, 100, 100)).toEqual(rectQuad(15, 7, 55, 47))
  expect(translateQuad(q, 500, -500, 100, 100)).toEqual(rectQuad(60, 0, 100, 40))
})

it('creates a new centred part', () => {
  expect(newPartQuad(1000, 800)).toEqual(rectQuad(425, 340, 575, 460))
})
```

`frontend/src/lib/estimate.test.ts`:
```ts
import { expect, it } from 'vitest'
import { groupByCategory } from './estimate'
import type { EstimateLine } from './types'

const line = (category: string, materialCost: number, laborCost: number) =>
  ({ category, materialCost, laborCost, total: materialCost + laborCost }) as EstimateLine

it('groups lines by category in first-seen order with subtotals', () => {
  const groups = groupByCategory([line('Paint', 100, 50), line('Railing', 900, 100), line('Paint', 10, 5)])
  expect(groups.map((g) => g.category)).toEqual(['Paint', 'Railing'])
  expect(groups[0]).toMatchObject({ materialCost: 110, laborCost: 55, total: 165 })
  expect(groups[0].lines).toHaveLength(2)
  expect(groups[1].total).toBe(1000)
})
```

- [ ] **Step 2: Run to verify they fail**

Run: `npx vitest run src/lib`
Expected: FAIL — unresolved `./steps`, `./quad`, `./estimate`.

- [ ] **Step 3: Implement**

`frontend/src/lib/steps.ts`:
```ts
import type { Project } from './types'

export const STEPS = [
  { key: 'photo', label: 'Photo' },
  { key: 'parts', label: 'Parts' },
  { key: 'design', label: 'Design' },
  { key: 'preview', label: 'Preview' },
  { key: 'estimate', label: 'Estimate' },
  { key: 'report', label: 'Report' },
] as const
export type StepKey = (typeof STEPS)[number]['key']

export function unlockedSteps(project: Project | null): Set<StepKey> {
  const open = new Set<StepKey>(['photo'])
  if (!project?.primaryPhotoId) return open
  open.add('parts')
  if (project.components.length > 0) open.add('design')
  if (project.designs.length > 0) {
    open.add('preview')
    open.add('estimate')
    open.add('report')
  }
  return open
}

export function resumeStep(project: Project): StepKey {
  const open = unlockedSteps(project)
  if (open.has('design')) return 'design'
  if (open.has('parts')) return 'parts'
  return 'photo'
}
```

`frontend/src/lib/quad.ts`:
```ts
import type { Point, Quad } from './types'

// New parts start as a box this fraction of the photo's width/height.
const NEW_PART_FRACTION = 0.15

export const rectQuad = (x0: number, y0: number, x1: number, y1: number): Quad => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

export function clampPoint([x, y]: Point, width: number, height: number): Point {
  return [Math.min(Math.max(x, 0), width), Math.min(Math.max(y, 0), height)]
}

export function moveCorner(quad: Quad, index: number, point: Point, width: number, height: number): Quad {
  return quad.map((p, i) => (i === index ? clampPoint(point, width, height) : p)) as Quad
}

export function translateQuad(quad: Quad, dx: number, dy: number, width: number, height: number): Quad {
  const xs = quad.map((p) => p[0])
  const ys = quad.map((p) => p[1])
  const sx = Math.min(Math.max(dx, -Math.min(...xs)), width - Math.max(...xs))
  const sy = Math.min(Math.max(dy, -Math.min(...ys)), height - Math.max(...ys))
  return quad.map(([x, y]) => [x + sx, y + sy]) as Quad
}

export function newPartQuad(width: number, height: number): Quad {
  const w = width * NEW_PART_FRACTION
  const h = height * NEW_PART_FRACTION
  return rectQuad(width / 2 - w / 2, height / 2 - h / 2, width / 2 + w / 2, height / 2 + h / 2)
}
```

`frontend/src/lib/estimate.ts`:
```ts
import type { EstimateLine } from './types'

export interface CategoryGroup {
  category: string
  lines: EstimateLine[]
  materialCost: number
  laborCost: number
  total: number
}

export function groupByCategory(lines: EstimateLine[]): CategoryGroup[] {
  const groups = new Map<string, CategoryGroup>()
  for (const line of lines) {
    const g = groups.get(line.category) ?? { category: line.category, lines: [], materialCost: 0, laborCost: 0, total: 0 }
    g.lines.push(line)
    g.materialCost += line.materialCost
    g.laborCost += line.laborCost
    g.total += line.total
    groups.set(line.category, g)
  }
  return [...groups.values()]
}
```

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/lib`
Expected: `14 passed` (6 from Task 2 + 8 new).

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/lib && git commit -m "feat: add step gating, region geometry and cost grouping

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: API client

**Files:**
- Create: `frontend/src/lib/api.ts`
- Test: `frontend/src/lib/api.test.ts`

**Interfaces:**
- Consumes: `keysToCamel`, `keysToSnake`, types (Task 2).
- Produces: `class ApiError extends Error { code: string; status: number }`, `errorMessage(e: unknown): string`, and `api` with:
  `createProject(name?) · getProject(id) · updateProject(id, {name?, state?, city?}) · uploadPhoto(projectId, file) · setPrimary(projectId, photoId) · detect(projectId) · saveParts(projectId, parts) · setScale(projectId, {componentId, realHeightFt} | {useDefault: true})` → `Promise<Project>`;
  `catalog() → Material[]`, `locations() → StateEntry[]`, `rates(state, city, projectId) → RateRow[]`, `overrideRate(projectId, materialId, {materialRate?, laborRate?}) → RateRow[]`, `designFromText(projectId, text) → Design[]`, `recommend(projectId, answers) → Design[]`, `saveDesign(projectId, {id?, name, spec}) → Design`, `render(designId) → Design`, `estimate(designId) → Estimate`, `reportUrl(designId) → string`.

- [ ] **Step 1: Write the failing tests**

`frontend/src/lib/api.test.ts`:
```ts
import { afterEach, expect, it, vi } from 'vitest'
import { api } from './api'

afterEach(() => vi.unstubAllGlobals())

function stubFetch(status: number, body: string) {
  const fn = vi.fn().mockResolvedValue(new Response(body, { status, headers: { 'Content-Type': 'application/json' } }))
  vi.stubGlobal('fetch', fn)
  return fn
}

it('sends snake_case bodies and returns camelCase data', async () => {
  const fn = stubFetch(200, JSON.stringify({ designs: [{ id: 'd', render_url: null }] }))
  const designs = await api.designFromText('p1', 'grey walls')
  expect(fn).toHaveBeenCalledWith('/api/design/from-text?project_id=p1', expect.objectContaining({
    method: 'POST', body: JSON.stringify({ text: 'grey walls' }),
  }))
  expect(designs[0].renderUrl).toBeNull()
})

it('converts nested spec keys when saving a design', async () => {
  const fn = stubFetch(200, JSON.stringify({ designs: [{ id: 'd' }] }))
  await api.saveDesign('p1', {
    name: 'A',
    spec: { style: '', palette: [], keepUnchanged: ['window'], assignments: [{ target: 'type:wall', materialId: 'x', color: null, finish: '' }] },
  })
  const body = JSON.parse(fn.mock.calls[0][1].body)
  expect(body.spec.keep_unchanged).toEqual(['window'])
  expect(body.spec.assignments[0].material_id).toBe('x')
})

it('surfaces the backend error message and code', async () => {
  stubFetch(429, JSON.stringify({ error: { code: 'RENDER_LIMIT', message: 'Used all 8 previews.', status: 429, details: [] } }))
  await expect(api.render('d')).rejects.toMatchObject({ code: 'RENDER_LIMIT', status: 429, message: 'Used all 8 previews.' })
})

it('falls back to a friendly message for non-JSON errors', async () => {
  stubFetch(502, '<html>Bad gateway</html>')
  await expect(api.getProject('p')).rejects.toMatchObject({ status: 502, message: 'Something went wrong. Try again.' })
})

it('reports network failures plainly', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
  await expect(api.catalog()).rejects.toMatchObject({ code: 'NETWORK', status: 0 })
})

it('uploads photos as multipart without a JSON content type', async () => {
  const fn = stubFetch(200, JSON.stringify({ id: 'p', photos: [] }))
  await api.uploadPhoto('p', new File(['x'], 'h.jpg', { type: 'image/jpeg' }))
  const init = fn.mock.calls[0][1]
  expect(init.body).toBeInstanceOf(FormData)
  expect(init.headers).toBeUndefined()
})
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run src/lib/api.test.ts`
Expected: FAIL — unresolved `./api`.

- [ ] **Step 3: Implement**

`frontend/src/lib/api.ts`:
```ts
import { keysToCamel, keysToSnake } from './case'
import type { Answers, Design, DesignSpec, Estimate, Material, Part, Project, RateRow, StateEntry } from './types'

const BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')
const FALLBACK = 'Something went wrong. Try again.'

export class ApiError extends Error {
  constructor(message: string, public code: string, public status: number) {
    super(message)
  }
}

export const errorMessage = (e: unknown) => (e instanceof ApiError ? e.message : FALLBACK)

type Query = Record<string, string | undefined>

async function request<T>(method: 'GET' | 'POST', path: string, opts: { query?: Query; body?: unknown; form?: FormData } = {}): Promise<T> {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(opts.query ?? {})) if (v !== undefined) params.set(k, v)
  const qs = params.toString()
  const url = `${BASE}${path}${qs ? `?${qs}` : ''}`
  const init: RequestInit = { method }
  if (opts.form) {
    init.body = opts.form
  } else if (opts.body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' }
    init.body = JSON.stringify(keysToSnake(opts.body))
  }

  let res: Response
  try {
    res = await fetch(url, init)
  } catch {
    throw new ApiError('Cannot reach the server. Check your connection and try again.', 'NETWORK', 0)
  }
  if (!res.ok) {
    let message = FALLBACK
    let code = 'UNKNOWN'
    try {
      const data = await res.json()
      message = data?.error?.message ?? message
      code = data?.error?.code ?? code
    } catch {
      // Non-JSON error page (proxy/gateway); keep the friendly fallback.
    }
    throw new ApiError(message, code, res.status)
  }
  return keysToCamel<T>(await res.json())
}

export const api = {
  createProject: (name?: string) => request<Project>('POST', '/api/project/create', { body: { name } }),
  getProject: (id: string) => request<Project>('GET', '/api/project', { query: { id } }),
  updateProject: (id: string, patch: { name?: string; state?: string; city?: string }) =>
    request<Project>('POST', '/api/project/update', { query: { id }, body: patch }),
  uploadPhoto: (projectId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<Project>('POST', '/api/photo/upload', { query: { project_id: projectId }, form })
  },
  setPrimary: (projectId: string, photoId: string) =>
    request<Project>('POST', '/api/photo/set-primary', { query: { project_id: projectId }, body: { photoId } }),
  detect: (projectId: string) => request<Project>('POST', '/api/structure/detect', { query: { project_id: projectId } }),
  saveParts: (projectId: string, components: Part[]) =>
    request<Project>('POST', '/api/structure/save', { query: { project_id: projectId }, body: { components } }),
  setScale: (projectId: string, input: { componentId: string; realHeightFt: number } | { useDefault: true }) =>
    request<Project>('POST', '/api/scale/set', { query: { project_id: projectId }, body: input }),
  catalog: () => request<{ materials: Material[] }>('GET', '/api/catalog').then((r) => r.materials),
  locations: () => request<{ states: StateEntry[] }>('GET', '/api/locations').then((r) => r.states),
  rates: (state: string, city: string, projectId: string) =>
    request<{ rates: RateRow[] }>('GET', '/api/rates', { query: { state, city, project_id: projectId } }).then((r) => r.rates),
  overrideRate: (projectId: string, materialId: string, rates: { materialRate?: number; laborRate?: number }) =>
    request<{ rates: RateRow[] }>('POST', '/api/rates/override', { query: { project_id: projectId }, body: { materialId, ...rates } })
      .then((r) => r.rates),
  designFromText: (projectId: string, text: string) =>
    request<{ designs: Design[] }>('POST', '/api/design/from-text', { query: { project_id: projectId }, body: { text } })
      .then((r) => r.designs),
  recommend: (projectId: string, answers: Answers) =>
    request<{ designs: Design[] }>('POST', '/api/design/recommend', { query: { project_id: projectId }, body: answers })
      .then((r) => r.designs),
  saveDesign: (projectId: string, design: { id?: string; name: string; spec: DesignSpec }) =>
    request<{ designs: Design[] }>('POST', '/api/design/save', { query: { project_id: projectId }, body: design })
      .then((r) => r.designs[0]),
  render: (designId: string) => request<Design>('POST', '/api/design/render', { query: { id: designId } }),
  estimate: (designId: string) => request<Estimate>('GET', '/api/estimate', { query: { design_id: designId } }),
  reportUrl: (designId: string) => `${BASE}/api/report?design_id=${encodeURIComponent(designId)}`,
}
```

- [ ] **Step 4: Run tests + build**

Run: `npx vitest run && npm run build`
Expected: `20 passed`; build succeeds.

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/lib && git commit -m "feat: add typed API client with friendly errors

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: App shell, step rail, hooks

**Files:**
- Create: `frontend/src/lib/hooks.ts`, `frontend/src/components/StepRail.tsx`
- Modify: `frontend/src/App.tsx` (replace placeholder)
- Create stubs (replaced by Tasks 6–11) so the shell compiles: `frontend/src/steps/PhotoStep.tsx`, `PartsStep.tsx`, `DesignStep.tsx`, `PreviewStep.tsx`, `EstimateStep.tsx`, `ReportStep.tsx`

**Interfaces:**
- Produces:
  - `useElapsed(active: boolean): number` (seconds), `useCountUp(value: number): number`
  - Step component props (later tasks must keep these exactly):
    - `PhotoStep { project: Project | null; states: StateEntry[]; ensureProject: () => Promise<Project>; onChange: (p: Project) => void; onNext: () => void }`
    - `PartsStep { project: Project; onChange: (p: Project) => void; onNext: () => void }`
    - `DesignStep { project: Project; catalog: Material[]; activeDesignId: string | null; onChange: (p: Project) => void; onSelectDesign: (id: string) => void; onNext: () => void }`
    - `PreviewStep { project: Project; design: Design; onChange: (p: Project) => void; onSelectDesign: (id: string) => void; onNext: () => void }`
    - `EstimateStep { project: Project; design: Design; onNext: () => void }`
    - `ReportStep { project: Project; design: Design }`

- [ ] **Step 1: Hooks**

`frontend/src/lib/hooks.ts`:
```ts
import { useEffect, useRef, useState } from 'react'

const COUNT_UP_MS = 400

export function useElapsed(active: boolean): number {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    if (!active) {
      setSeconds(0)
      return
    }
    const start = Date.now()
    const timer = setInterval(() => setSeconds(Math.round((Date.now() - start) / 1000)), 1000)
    return () => clearInterval(timer)
  }, [active])
  return seconds
}

export function useCountUp(value: number): number {
  const [shown, setShown] = useState(value)
  const from = useRef(value)
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      from.current = value
      setShown(value)
      return
    }
    const start = performance.now()
    const origin = from.current
    let frame = 0
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / COUNT_UP_MS)
      setShown(Math.round(origin + (value - origin) * (1 - (1 - t) ** 3)))
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(frame)
      from.current = value
    }
  }, [value])
  return shown
}
```

- [ ] **Step 2: Step rail**

`frontend/src/components/StepRail.tsx`:
```tsx
import type { CSSProperties } from 'react'
import { STEPS, type StepKey } from '../lib/steps'

interface Props {
  step: StepKey
  unlocked: Set<StepKey>
  onSelect: (step: StepKey) => void
}

export default function StepRail({ step, unlocked, onSelect }: Props) {
  const index = STEPS.findIndex((s) => s.key === step)
  return (
    <>
      <nav className="rail" aria-label="Steps">
        <span className="wordmark">Facade</span>
        <ol>
          {STEPS.map((s, i) => (
            <li key={s.key}>
              <button
                type="button"
                className="step-link"
                aria-current={s.key === step ? 'step' : undefined}
                disabled={!unlocked.has(s.key)}
                onClick={() => onSelect(s.key)}
              >
                <span className="num">{String(i + 1).padStart(2, '0')}</span>
                {s.label}
              </button>
            </li>
          ))}
        </ol>
      </nav>
      <div className="mobile-bar">
        <div className="inner">
          <span>
            Step {index + 1} of {STEPS.length} · <strong>{STEPS[index].label}</strong>
          </span>
          <label className="sr-only" htmlFor="step-jump">Go to step</label>
          <select id="step-jump" className="step-jump" value={step} onChange={(e) => onSelect(e.target.value as StepKey)}>
            {STEPS.map((s) => (
              <option key={s.key} value={s.key} disabled={!unlocked.has(s.key)}>{s.label}</option>
            ))}
          </select>
        </div>
        <div className="progress" style={{ '--done': (index + 1) / STEPS.length } as CSSProperties} />
      </div>
    </>
  )
}
```

- [ ] **Step 3: Step stubs**

Each stub file exports a default component with the exact props interface from **Interfaces** above and renders `<section><h1>…</h1></section>`. Example `frontend/src/steps/PartsStep.tsx`:
```tsx
import type { Project } from '../lib/types'

interface Props {
  project: Project
  onChange: (p: Project) => void
  onNext: () => void
}

export default function PartsStep({ project }: Props) {
  return <section><h1>Parts for {project.name}</h1></section>
}
```
Write the other five the same way (use one prop in the JSX so `noUnusedParameters` stays quiet; unused props are fine because destructuring only what you use is allowed).

- [ ] **Step 4: App**

`frontend/src/App.tsx`:
```tsx
import { useCallback, useEffect, useState } from 'react'
import StepRail from './components/StepRail'
import { api, errorMessage } from './lib/api'
import { resumeStep, unlockedSteps, type StepKey } from './lib/steps'
import type { Material, Project, StateEntry } from './lib/types'
import DesignStep from './steps/DesignStep'
import EstimateStep from './steps/EstimateStep'
import PartsStep from './steps/PartsStep'
import PhotoStep from './steps/PhotoStep'
import PreviewStep from './steps/PreviewStep'
import ReportStep from './steps/ReportStep'

export default function App() {
  const [project, setProject] = useState<Project | null>(null)
  const [catalog, setCatalog] = useState<Material[]>([])
  const [states, setStates] = useState<StateEntry[]>([])
  const [step, setStep] = useState<StepKey>('photo')
  const [designId, setDesignId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.catalog().then(setCatalog).catch((e) => setError(errorMessage(e)))
    api.locations().then(setStates).catch((e) => setError(errorMessage(e)))
    const id = new URLSearchParams(window.location.search).get('p')
    if (id) {
      api.getProject(id)
        .then((p) => {
          setProject(p)
          setStep(resumeStep(p))
        })
        .catch((e) => setError(errorMessage(e)))
    }
  }, [])

  const ensureProject = useCallback(async () => {
    if (project) return project
    const created = await api.createProject()
    window.history.replaceState(null, '', `?p=${created.id}`)
    setProject(created)
    return created
  }, [project])

  const unlocked = unlockedSteps(project)
  const design = project?.designs.find((d) => d.id === designId) ?? project?.designs[0] ?? null
  const go = (next: StepKey) => {
    setStep(next)
    window.scrollTo({ top: 0 })
  }

  return (
    <div className="app">
      <StepRail step={step} unlocked={unlocked} onSelect={go} />
      <main key={step} className="fade-in">
        {error && (
          <p className="notice error" role="alert">
            {error} <a href="/">Start a new project</a>
          </p>
        )}
        {step === 'photo' && (
          <PhotoStep project={project} states={states} ensureProject={ensureProject} onChange={setProject} onNext={() => go('parts')} />
        )}
        {step === 'parts' && project && <PartsStep project={project} onChange={setProject} onNext={() => go('design')} />}
        {step === 'design' && project && (
          <DesignStep
            project={project}
            catalog={catalog}
            activeDesignId={design?.id ?? null}
            onChange={setProject}
            onSelectDesign={setDesignId}
            onNext={() => go('preview')}
          />
        )}
        {step === 'preview' && project && design && (
          <PreviewStep project={project} design={design} onChange={setProject} onSelectDesign={setDesignId} onNext={() => go('estimate')} />
        )}
        {step === 'estimate' && project && design && <EstimateStep project={project} design={design} onNext={() => go('report')} />}
        {step === 'report' && project && design && <ReportStep project={project} design={design} />}
        <footer className="footer">
          Advisory estimate from one photo. Confirm measurements and prices with your contractor before work begins.
        </footer>
      </main>
    </div>
  )
}
```

- [ ] **Step 5: Build**

Run: `npm run build && npx vitest run`
Expected: build succeeds; `20 passed`.

- [ ] **Step 6: Commit**

```bash
cd .. && git add frontend/src && git commit -m "feat: add app shell with step rail and project loading

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: 01 Photo step + city picker

**Files:**
- Create: `frontend/src/components/CitySelect.tsx`
- Modify: `frontend/src/steps/PhotoStep.tsx` (replace stub)

**Interfaces:**
- Consumes: `api.uploadPhoto`, `api.setPrimary`, `api.updateProject`, `errorMessage`, `useElapsed`, `StateEntry`.
- Produces: `CitySelect { states: StateEntry[]; state: string; city: string; onSave: (state: string, city: string) => Promise<void> }` (reused by Estimate step).

- [ ] **Step 1: CitySelect**

`frontend/src/components/CitySelect.tsx`:
```tsx
import { useEffect, useState } from 'react'
import { errorMessage } from '../lib/api'
import type { StateEntry } from '../lib/types'

const OTHER = '__other'

interface Props {
  states: StateEntry[]
  state: string
  city: string
  onSave: (state: string, city: string) => Promise<void>
}

export default function CitySelect({ states, state, city, onSave }: Props) {
  const [s, setS] = useState(state)
  const [c, setC] = useState(city)
  const [otherChosen, setOtherChosen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)

  useEffect(() => {
    setS(state)
    setC(city)
  }, [state, city])

  const cities = states.find((x) => x.name === s)?.cities ?? []
  const other = otherChosen || (c !== '' && !cities.some((x) => x.name === c))

  async function save() {
    setBusy(true)
    setMsg(null)
    try {
      await onSave(s, c.trim())
      setMsg({ kind: 'ok', text: `Rates will use ${c.trim()}, ${s}.` })
    } catch (e) {
      setMsg({ kind: 'error', text: errorMessage(e) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="stack">
      <div className="field">
        <label htmlFor="state">State</label>
        <select id="state" value={s} onChange={(e) => { setS(e.target.value); setC(''); setOtherChosen(false) }}>
          <option value="">Choose a state</option>
          {states.map((x) => <option key={x.name} value={x.name}>{x.name}</option>)}
        </select>
      </div>
      <div className="field">
        <label htmlFor="city">City</label>
        <select
          id="city"
          value={other ? OTHER : c}
          disabled={!s}
          onChange={(e) => {
            const v = e.target.value
            setOtherChosen(v === OTHER)
            setC(v === OTHER ? '' : v)
          }}
        >
          <option value="">Choose a city</option>
          {cities.map((x) => <option key={x.name} value={x.name}>{x.name}</option>)}
          <option value={OTHER}>Other city</option>
        </select>
      </div>
      {other && (
        <div className="field">
          <label htmlFor="city-other">City name</label>
          <input id="city-other" type="text" maxLength={80} value={c} onChange={(e) => setC(e.target.value)} />
        </div>
      )}
      <button type="button" className="btn" disabled={!s || !c.trim() || busy} aria-busy={busy} onClick={save}>
        {busy ? 'Saving…' : 'Save location'}
      </button>
      {msg && <p className={`notice ${msg.kind}`} role="status">{msg.text}</p>}
    </div>
  )
}
```

- [ ] **Step 2: PhotoStep**

`frontend/src/steps/PhotoStep.tsx`:
```tsx
import { useState } from 'react'
import CitySelect from '../components/CitySelect'
import { api, errorMessage } from '../lib/api'
import { useElapsed } from '../lib/hooks'
import type { Project, StateEntry } from '../lib/types'

interface Props {
  project: Project | null
  states: StateEntry[]
  ensureProject: () => Promise<Project>
  onChange: (p: Project) => void
  onNext: () => void
}

export default function PhotoStep({ project, states, ensureProject, onChange, onNext }: Props) {
  const [busy, setBusy] = useState(false)
  const [over, setOver] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const elapsed = useElapsed(busy)

  async function upload(file: File) {
    setBusy(true)
    setError(null)
    try {
      const p = await ensureProject()
      onChange(await api.uploadPhoto(p.id, file))
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  async function makePrimary(photoId: string) {
    if (!project) return
    setError(null)
    try {
      onChange(await api.setPrimary(project.id, photoId))
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  async function saveLocation(state: string, city: string) {
    const p = await ensureProject()
    onChange(await api.updateProject(p.id, { state, city }))
  }

  const pick = (files: FileList | null) => {
    const file = files?.[0]
    if (file) void upload(file)
  }

  return (
    <section aria-labelledby="photo-h">
      <header className="stage-head">
        <p className="label">01 · Photo</p>
        <h1 id="photo-h">Start with one clear photo of the front.</h1>
        <p className="lede">Stand across the road in daylight so the whole front fits. We check every photo before using it.</p>
      </header>
      <div className="workspace">
        <div className="stack">
          <label
            className="dropzone"
            data-over={over}
            onDragOver={(e) => { e.preventDefault(); setOver(true) }}
            onDragLeave={() => setOver(false)}
            onDrop={(e) => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files) }}
          >
            <input
              className="sr-only"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={busy}
              onChange={(e) => { pick(e.target.files); e.target.value = '' }}
            />
            <strong>{busy ? `Checking your photo… ${elapsed}s` : 'Choose a photo or drop it here'}</strong>
            <span className="lede">JPG, PNG or WEBP · at least 800 px on the short side · up to 15 MB</span>
          </label>
          {error && <p className="notice error" role="alert">{error}</p>}
          {project && project.photos.length > 0 && (
            <ul className="thumbs" aria-label="Your photos">
              {project.photos.map((ph) => (
                <li key={ph.id} className="thumb" data-primary={ph.id === project.primaryPhotoId}>
                  <img src={ph.url} alt="Uploaded photo of the house" />
                  {ph.qualityOk ? (
                    ph.id === project.primaryPhotoId ? (
                      <span className="badge web">In use</span>
                    ) : (
                      <button type="button" className="btn btn-small" onClick={() => makePrimary(ph.id)}>Use this photo</button>
                    )
                  ) : (
                    <div className="notice error">
                      <strong>Can't use this one</strong>
                      <ul>{[...ph.issues, ...ph.tips].map((t) => <li key={t}>{t}</li>)}</ul>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
        <aside className="panel">
          <h2>Where is the house?</h2>
          <p className="lede">Material and labour rates are looked up for your city.</p>
          <CitySelect states={states} state={project?.state ?? ''} city={project?.city ?? ''} onSave={saveLocation} />
          <button type="button" className="btn btn-primary" disabled={!project?.primaryPhotoId} onClick={onNext}>
            Next: check the parts
          </button>
        </aside>
      </div>
    </section>
  )
}
```

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: succeeds, no TS errors.

- [ ] **Step 4: Commit**

```bash
cd .. && git add frontend/src && git commit -m "feat: add photo upload step and city picker

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: 02 Parts step + region editor

**Files:**
- Create: `frontend/src/components/RegionCanvas.tsx`
- Modify: `frontend/src/steps/PartsStep.tsx` (replace stub)

**Interfaces:**
- Consumes: `api.detect`, `api.saveParts`, `api.setScale`, quad helpers (Task 3), `COMPONENT_TYPES`, `typeLabel`, `useElapsed`.
- Produces: `RegionCanvas { src: string; width: number; height: number; parts: Part[]; selected: number | null; onSelect: (i: number | null) => void; onChange: (i: number, quad: Quad) => void }`.

- [ ] **Step 1: RegionCanvas**

`frontend/src/components/RegionCanvas.tsx`:
```tsx
import { useEffect, useMemo, useRef, useState } from 'react'
import { Circle, Image as KImage, Layer, Line, Stage } from 'react-konva'
import { moveCorner, translateQuad } from '../lib/quad'
import { COMPONENT_TYPES, type Part, type Quad } from '../lib/types'

const HANDLE_RADIUS = 9
const HIT_WIDTH = 14

interface Props {
  src: string
  width: number
  height: number
  parts: Part[]
  selected: number | null
  onSelect: (index: number | null) => void
  onChange: (index: number, quad: Quad) => void
}

// Konva draws on <canvas>, so read the region tokens once from CSS.
function useTokenColors() {
  return useMemo(() => {
    const css = getComputedStyle(document.documentElement)
    const read = (name: string) => css.getPropertyValue(name).trim()
    return {
      regions: Object.fromEntries(COMPONENT_TYPES.map((t) => [t, read(`--region-${t}`)])) as Record<string, string>,
      paper: read('--color-paper'),
      ink: read('--color-ink'),
    }
  }, [])
}

export default function RegionCanvas({ src, width, height, parts, selected, onSelect, onChange }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [boxWidth, setBoxWidth] = useState(0)
  const [image, setImage] = useState<HTMLImageElement | null>(null)
  const colors = useTokenColors()

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => setBoxWidth(entry.contentRect.width))
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const img = new window.Image()
    img.onload = () => setImage(img)
    img.src = src
    return () => { img.onload = null }
  }, [src])

  const scale = boxWidth > 0 ? boxWidth / width : 0
  const active = selected !== null ? parts[selected] : undefined

  return (
    <div ref={wrapRef} className="canvas-wrap">
      {scale > 0 && (
        <Stage
          width={boxWidth}
          height={height * scale}
          onMouseDown={(e) => { if (e.target.getClassName() === 'Image') onSelect(null) }}
          onTouchStart={(e) => { if (e.target.getClassName() === 'Image') onSelect(null) }}
        >
          <Layer>
            {image && <KImage image={image} width={width * scale} height={height * scale} />}
            {parts.map((p, i) => (
              <Line
                key={p.id ?? `new-${i}`}
                points={p.quad.flatMap(([x, y]) => [x * scale, y * scale])}
                closed
                fill="transparent"
                stroke={colors.regions[p.type]}
                strokeWidth={i === selected ? 3 : 2}
                hitStrokeWidth={HIT_WIDTH}
                draggable={i === selected}
                onClick={() => onSelect(i)}
                onTap={() => onSelect(i)}
                onDragEnd={(e) => {
                  const node = e.target
                  const dx = node.x() / scale
                  const dy = node.y() / scale
                  node.position({ x: 0, y: 0 })
                  onChange(i, translateQuad(p.quad, dx, dy, width, height))
                }}
              />
            ))}
            {selected !== null && active && active.quad.map(([x, y], k) => (
              <Circle
                key={k}
                x={x * scale}
                y={y * scale}
                radius={HANDLE_RADIUS}
                fill={colors.paper}
                stroke={colors.ink}
                strokeWidth={2}
                draggable
                onDragMove={(e) => onChange(selected, moveCorner(active.quad, k, [e.target.x() / scale, e.target.y() / scale], width, height))}
              />
            ))}
          </Layer>
        </Stage>
      )}
    </div>
  )
}
```

- [ ] **Step 2: PartsStep**

`frontend/src/steps/PartsStep.tsx`:
```tsx
import { useEffect, useState } from 'react'
import RegionCanvas from '../components/RegionCanvas'
import { api, errorMessage } from '../lib/api'
import { num, typeLabel } from '../lib/format'
import { useElapsed } from '../lib/hooks'
import { newPartQuad } from '../lib/quad'
import { COMPONENT_TYPES, type ComponentType, type Part, type Project } from '../lib/types'

interface Props {
  project: Project
  onChange: (p: Project) => void
  onNext: () => void
}

type Busy = 'detect' | 'save' | 'scale' | null

export default function PartsStep({ project, onChange, onNext }: Props) {
  const photo = project.photos.find((p) => p.id === project.primaryPhotoId)
  const [parts, setParts] = useState<Part[]>(project.components)
  const [selected, setSelected] = useState<number | null>(null)
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState<Busy>(null)
  const [error, setError] = useState<string | null>(null)
  const [scalePart, setScalePart] = useState('')
  const [scaleFt, setScaleFt] = useState('')
  const elapsed = useElapsed(busy === 'detect')

  useEffect(() => {
    setParts(project.components)
    setDirty(false)
    setSelected(null)
  }, [project.components])

  if (!photo) {
    return <p className="notice error" role="alert">Choose a usable photo on step 01 first.</p>
  }

  async function run(kind: Exclude<Busy, null>, action: () => Promise<Project>) {
    setBusy(kind)
    setError(null)
    try {
      onChange(await action())
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(null)
    }
  }

  const edit = (i: number, patch: Partial<Part>) => {
    setParts((ps) => ps.map((p, j) => (j === i ? { ...p, ...patch, source: 'user' } : p)))
    setDirty(true)
  }
  const add = () => {
    setParts((ps) => [...ps, { type: 'wall', quad: newPartQuad(photo.width, photo.height), floor: 0, source: 'user' }])
    setSelected(parts.length)
    setDirty(true)
  }
  const remove = (i: number) => {
    setParts((ps) => ps.filter((_, j) => j !== i))
    setSelected(null)
    setDirty(true)
  }
  const savedParts = project.components.filter((p) => p.id)
  const ft = Number(scaleFt)

  return (
    <section aria-labelledby="parts-h">
      <header className="stage-head">
        <p className="label">02 · Parts</p>
        <h1 id="parts-h">Check what we found on your house.</h1>
        <p className="lede">Each coloured outline is a part we will price. Tap one to drag it or its corners; fix the type in the list.</p>
      </header>
      <div className="workspace">
        <div className="stack">
          <RegionCanvas
            src={photo.url}
            width={photo.width}
            height={photo.height}
            parts={parts}
            selected={selected}
            onSelect={setSelected}
            onChange={(i, quad) => edit(i, { quad })}
          />
          {busy === 'detect' && <p className="progress-line" role="status">Finding walls, windows and pillars… {elapsed}s</p>}
          {error && <p className="notice error" role="alert">{error}</p>}
        </div>
        <aside className="panel">
          <div className="row">
            <button type="button" className="btn btn-primary" disabled={busy !== null} aria-busy={busy === 'detect'}
              onClick={() => run('detect', () => api.detect(project.id))}>
              {parts.length ? 'Find parts again' : 'Find parts'}
            </button>
            <button type="button" className="btn" onClick={add}>Add a part</button>
          </div>
          {parts.length === 0 ? (
            <p className="notice">No parts yet. Find them automatically, or add one and drag its corners.</p>
          ) : (
            <ul className="part-list" aria-label="Parts">
              {parts.map((p, i) => (
                <li key={p.id ?? `new-${i}`} className="part-row" aria-selected={i === selected}>
                  <span className="swatch" style={{ background: `var(--region-${p.type})` }} aria-hidden="true" />
                  <select aria-label={`Part ${i + 1} type`} value={p.type} onChange={(e) => edit(i, { type: e.target.value as ComponentType })}>
                    {COMPONENT_TYPES.map((t) => <option key={t} value={t}>{typeLabel(t)}</option>)}
                  </select>
                  <div className="row">
                    <button type="button" className="btn btn-small" aria-pressed={i === selected} onClick={() => setSelected(i)}>Edit</button>
                    <button type="button" className="btn btn-small" aria-label={`Delete part ${i + 1}`} onClick={() => remove(i)}>Delete</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <button type="button" className="btn" disabled={!dirty || busy !== null} aria-busy={busy === 'save'}
            onClick={() => run('save', () => api.saveParts(project.id, parts))}>
            {busy === 'save' ? 'Saving…' : 'Save parts'}
          </button>

          <h2>Real size</h2>
          <p className="lede">
            {project.scaleSource === 'user'
              ? `Using your measurement (${num(project.pxPerFt ?? 0)} px per ft).`
              : 'Using a standard 7 ft door or 4 ft window. Enter one real height for a better estimate.'}
          </p>
          <div className="field">
            <label htmlFor="scale-part">Part you measured</label>
            <select id="scale-part" value={scalePart} onChange={(e) => setScalePart(e.target.value)}>
              <option value="">Choose a part</option>
              {savedParts.map((p, i) => <option key={p.id} value={p.id}>{typeLabel(p.type)} {i + 1}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="scale-ft">Its height in feet</label>
            <input id="scale-ft" type="number" inputMode="decimal" min={1} max={100} step="0.5" value={scaleFt}
              aria-invalid={scaleFt !== '' && !(ft >= 1 && ft <= 100)} onChange={(e) => setScaleFt(e.target.value)} />
          </div>
          <div className="row">
            <button type="button" className="btn" disabled={!scalePart || !(ft >= 1 && ft <= 100) || busy !== null}
              onClick={() => run('scale', () => api.setScale(project.id, { componentId: scalePart, realHeightFt: ft }))}>
              Use this size
            </button>
            <button type="button" className="btn btn-small" disabled={busy !== null}
              onClick={() => run('scale', () => api.setScale(project.id, { useDefault: true }))}>
              Use standard sizes
            </button>
          </div>

          {dirty && <p className="notice warn">Save your changes before moving on.</p>}
          <button type="button" className="btn btn-primary" disabled={dirty || parts.length === 0} onClick={onNext}>
            Next: choose a design
          </button>
        </aside>
      </div>
    </section>
  )
}
```

Add to `frontend/src/styles.css` under `/* feedback */`:
```css
.progress-line { font-size: var(--text-sm); color: var(--color-ink-2); }
```

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: succeeds.

- [ ] **Step 4: Commit**

```bash
cd .. && git add frontend/src && git commit -m "feat: add part review step with editable regions and scale

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: 03 Design step

**Files:**
- Modify: `frontend/src/steps/DesignStep.tsx` (replace stub)

**Interfaces:**
- Consumes: `api.designFromText`, `api.recommend`, `api.saveDesign`, `Material`, `Answers`, `DesignSpec`, `typeLabel`, `useElapsed`.

- [ ] **Step 1: Implement**

`frontend/src/steps/DesignStep.tsx`:
```tsx
import { useMemo, useState } from 'react'
import { api, errorMessage } from '../lib/api'
import { typeLabel } from '../lib/format'
import { useElapsed } from '../lib/hooks'
import type { Answers, ComponentType, Design, DesignSpec, Material, Project } from '../lib/types'

type Tab = 'describe' | 'guided' | 'manual'
type Pick = { materialId: string; color: string | null }

const EXAMPLES = [
  'Light grey texture paint on the walls, slate cladding on the pillars, glass railing on the balcony',
  'Keep it simple: cream paint everywhere and black steel railings',
]
const CHOICES = {
  budget: [['low', 'Tight'], ['mid', 'Balanced'], ['high', 'Premium']],
  climate: [['moderate', 'Moderate'], ['heavy_rain', 'Heavy rain'], ['coastal', 'Coastal'], ['hot_dry', 'Hot and dry']],
  style: [['modern', 'Modern'], ['traditional', 'Traditional'], ['minimal', 'Minimal'], ['luxe', 'Luxe']],
  maintenance: [['low', 'Low upkeep'], ['medium', 'Some upkeep is fine']],
} as const
const MODE_LABEL: Record<Design['mode'], string> = { free_text: 'From your words', guided: 'Suggested', manual: 'Picked by you' }
// Neutral starting swatch for the colour picker; stored only when the user changes it.
const DEFAULT_SWATCH = '#d9d4cc'

interface Props {
  project: Project
  catalog: Material[]
  activeDesignId: string | null
  onChange: (p: Project) => void
  onSelectDesign: (id: string) => void
  onNext: () => void
}

export default function DesignStep({ project, catalog, activeDesignId, onChange, onSelectDesign, onNext }: Props) {
  const [tab, setTab] = useState<Tab>('describe')
  const [text, setText] = useState('')
  const [answers, setAnswers] = useState<Answers>({
    budget: 'mid', climate: 'moderate', style: 'modern', maintenance: 'low', colorMood: '', keepUnchanged: [],
  })
  const [picks, setPicks] = useState<Partial<Record<ComponentType, Pick>>>({})
  const [editing, setEditing] = useState<Design | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const elapsed = useElapsed(busy)

  const byId = useMemo(() => new Map(catalog.map((m) => [m.id, m])), [catalog])
  const present = useMemo(
    () => [...new Set(project.components.map((c) => c.type))].filter((t) => t !== 'window' && t !== 'door'),
    [project.components],
  )

  async function create(action: () => Promise<Design[]>) {
    setBusy(true)
    setError(null)
    try {
      const created = await action()
      const ids = new Set(created.map((d) => d.id))
      onChange({ ...project, designs: [...created, ...project.designs.filter((d) => !ids.has(d.id))] })
      onSelectDesign(created[0].id)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  function manualSpec(): DesignSpec {
    const assignments = Object.entries(picks)
      .filter(([, p]) => p?.materialId)
      .map(([type, p]) => ({ target: `type:${type}`, materialId: p?.materialId ?? '', color: p?.color ?? null, finish: '' }))
    return { style: '', palette: [], assignments, keepUnchanged: [] }
  }

  function startEdit(d: Design) {
    const next: Partial<Record<ComponentType, Pick>> = {}
    for (const a of d.spec.assignments) {
      if (a.target.startsWith('type:')) next[a.target.slice(5) as ComponentType] = { materialId: a.materialId, color: a.color }
    }
    setPicks(next)
    setEditing(d)
    setTab('manual')
  }

  const summary = (d: Design) =>
    d.spec.assignments.map((a) => `${byId.get(a.materialId)?.name ?? a.materialId} on ${typeLabel(a.target.split(':')[1] ?? '')}`).join(' · ')

  return (
    <section aria-labelledby="design-h">
      <header className="stage-head">
        <p className="label">03 · Design</p>
        <h1 id="design-h">Choose what goes where.</h1>
        <p className="lede">Describe it in your words, answer a few questions, or pick each material yourself.</p>
      </header>
      <div className="workspace">
        <div className="stack">
          <div className="tabs" role="tablist" aria-label="Ways to design">
            {(['describe', 'guided', 'manual'] as const).map((t) => (
              <button key={t} type="button" role="tab" className="tab" aria-selected={tab === t} onClick={() => setTab(t)}>
                {t === 'describe' ? 'Describe it' : t === 'guided' ? 'Help me choose' : 'Pick materials'}
              </button>
            ))}
          </div>

          {tab === 'describe' && (
            <div className="stack" role="tabpanel">
              <div className="field">
                <label htmlFor="design-text">What should the house look like?</label>
                <textarea id="design-text" maxLength={1000} value={text} onChange={(e) => setText(e.target.value)} />
              </div>
              <div className="chips" aria-label="Examples">
                {EXAMPLES.map((ex) => <button key={ex} type="button" className="chip" onClick={() => setText(ex)}>{ex.split(',')[0]}</button>)}
              </div>
              <button type="button" className="btn btn-primary" disabled={busy || text.trim().length < 3} aria-busy={busy}
                onClick={() => create(() => api.designFromText(project.id, text))}>
                {busy ? `Reading your request… ${elapsed}s` : 'Create design'}
              </button>
            </div>
          )}

          {tab === 'guided' && (
            <div className="stack" role="tabpanel">
              {(Object.keys(CHOICES) as (keyof typeof CHOICES)[]).map((key) => (
                <div key={key} className="field" role="group" aria-labelledby={`q-${key}`}>
                  <span id={`q-${key}`} className="field-label">{typeLabel(key)}</span>
                  <div className="chips">
                    {CHOICES[key].map(([value, label]) => (
                      <button key={value} type="button" className="chip" aria-pressed={answers[key] === value}
                        onClick={() => setAnswers((a) => ({ ...a, [key]: value }))}>{label}</button>
                    ))}
                  </div>
                </div>
              ))}
              <div className="field">
                <label htmlFor="mood">Colour mood (optional)</label>
                <input id="mood" type="text" maxLength={60} placeholder="warm earthy tones" value={answers.colorMood}
                  onChange={(e) => setAnswers((a) => ({ ...a, colorMood: e.target.value }))} />
              </div>
              <div className="field" role="group" aria-labelledby="q-keep">
                <span id="q-keep" className="field-label">Leave these as they are</span>
                <div className="chips">
                  {present.map((t) => (
                    <button key={t} type="button" className="chip" aria-pressed={answers.keepUnchanged.includes(t)}
                      onClick={() => setAnswers((a) => ({
                        ...a,
                        keepUnchanged: a.keepUnchanged.includes(t) ? a.keepUnchanged.filter((x) => x !== t) : [...a.keepUnchanged, t],
                      }))}>{typeLabel(t)}</button>
                  ))}
                </div>
              </div>
              <button type="button" className="btn btn-primary" disabled={busy} aria-busy={busy}
                onClick={() => create(() => api.recommend(project.id, answers))}>
                {busy ? `Putting options together… ${elapsed}s` : 'Suggest 3 designs'}
              </button>
            </div>
          )}

          {tab === 'manual' && (
            <div className="stack" role="tabpanel">
              {editing && <p className="notice">Editing “{editing.name}”. Saving updates it.</p>}
              {present.map((t) => {
                const options = catalog.filter((m) => m.appliesTo.includes(t))
                const pick = picks[t]
                const chosen = pick ? byId.get(pick.materialId) : undefined
                return (
                  <div key={t} className="field">
                    <label htmlFor={`m-${t}`}>{typeLabel(t)}</label>
                    <div className="row">
                      <select id={`m-${t}`} value={pick?.materialId ?? ''} style={{ flex: '1 1 200px' }}
                        onChange={(e) => setPicks((p) => ({ ...p, [t]: { materialId: e.target.value, color: p[t]?.color ?? null } }))}>
                        <option value="">Leave as it is</option>
                        {options.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                      </select>
                      <input type="color" aria-label={`${typeLabel(t)} colour`} disabled={!pick?.materialId}
                        value={pick?.color ?? DEFAULT_SWATCH}
                        onChange={(e) => setPicks((p) => ({ ...p, [t]: { materialId: p[t]?.materialId ?? '', color: e.target.value } }))} />
                    </div>
                    {chosen && <span className="badge">Lasts {chosen.durabilityYears} yrs · {chosen.maintenance} upkeep</span>}
                  </div>
                )
              })}
              <button type="button" className="btn btn-primary" disabled={busy || manualSpec().assignments.length === 0} aria-busy={busy}
                onClick={() => create(async () => [await api.saveDesign(project.id, { id: editing?.id, name: editing?.name ?? 'My design', spec: manualSpec() })])}>
                {editing ? 'Update design' : 'Save design'}
              </button>
            </div>
          )}
          {error && <p className="notice error" role="alert">{error}</p>}
        </div>

        <aside className="panel">
          <h2>Your designs</h2>
          {project.designs.length === 0 ? (
            <p className="notice">No designs yet. Create one on the left.</p>
          ) : (
            <div className="design-list">
              {project.designs.map((d) => (
                <article key={d.id} className="design" data-active={d.id === activeDesignId}>
                  <span className="badge">{MODE_LABEL[d.mode]}</span>
                  <h3>{d.name}</h3>
                  <p className="lede">{summary(d) || 'No materials applied.'}</p>
                  {d.rationale && <p>{d.rationale}</p>}
                  {d.warnings.length > 0 && <div className="notice warn"><ul>{d.warnings.map((w) => <li key={w}>{w}</li>)}</ul></div>}
                  <div className="row">
                    <button type="button" className="btn btn-small btn-primary" disabled={d.spec.assignments.length === 0}
                      onClick={() => { onSelectDesign(d.id); onNext() }}>Preview this</button>
                    <button type="button" className="btn btn-small" onClick={() => startEdit(d)}>Edit</button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </aside>
      </div>
    </section>
  )
}
```

- [ ] **Step 2: Build**

Run: `npm run build`
Expected: succeeds.

- [ ] **Step 3: Commit**

```bash
cd .. && git add frontend/src && git commit -m "feat: add design step with describe, guided and manual modes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: 04 Preview step + compare slider

**Files:**
- Create: `frontend/src/components/CompareSlider.tsx`
- Modify: `frontend/src/steps/PreviewStep.tsx` (replace stub)

**Interfaces:**
- Consumes: `api.render`, `api.getProject`, `useElapsed`.
- Produces: `CompareSlider { before: string; after: string; alt: string }`.

- [ ] **Step 1: CompareSlider**

`frontend/src/components/CompareSlider.tsx`:
```tsx
import { useState, type CSSProperties } from 'react'

interface Props {
  before: string
  after: string
  alt: string
}

export default function CompareSlider({ before, after, alt }: Props) {
  const [pos, setPos] = useState(50)
  return (
    <figure className="stack" style={{ margin: 0 }}>
      <div className="compare" style={{ '--pos': `${pos}%` } as CSSProperties}>
        <img src={before} alt={`${alt}, original`} />
        <img className="after" src={after} alt={`${alt}, redesigned`} />
        <span className="divider" aria-hidden="true" />
      </div>
      <input
        className="compare-range"
        type="range"
        min={0}
        max={100}
        value={pos}
        aria-label="Slide to compare original and redesigned"
        onChange={(e) => setPos(Number(e.target.value))}
      />
      <figcaption className="row" style={{ justifyContent: 'space-between' }}>
        <span className="label">Original</span>
        <span className="label">Redesigned</span>
      </figcaption>
    </figure>
  )
}
```

- [ ] **Step 2: PreviewStep**

`frontend/src/steps/PreviewStep.tsx`:
```tsx
import { useState } from 'react'
import CompareSlider from '../components/CompareSlider'
import { api, errorMessage } from '../lib/api'
import { useElapsed } from '../lib/hooks'
import type { Design, Project } from '../lib/types'

interface Props {
  project: Project
  design: Design
  onChange: (p: Project) => void
  onSelectDesign: (id: string) => void
  onNext: () => void
}

export default function PreviewStep({ project, design, onChange, onSelectDesign, onNext }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const elapsed = useElapsed(busy)
  const photo = project.photos.find((p) => p.id === project.primaryPhotoId)
  const left = project.renderCap - project.renderCount

  async function render() {
    setBusy(true)
    setError(null)
    try {
      await api.render(design.id)
      onChange(await api.getProject(project.id))
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section aria-labelledby="preview-h">
      <header className="stage-head">
        <p className="label">04 · Preview</p>
        <h1 id="preview-h">See your house with the new materials.</h1>
        <p className="lede">The structure stays the same; only surfaces and colours change. Treat it as a guide, not a photograph.</p>
      </header>
      <div className="workspace">
        <div className="stack">
          {photo && design.renderUrl ? (
            <CompareSlider before={photo.url} after={design.renderUrl} alt="Your house" />
          ) : (
            photo && <img src={photo.url} alt="Your house, original" />
          )}
          {busy && <p className="progress-line" role="status">Applying materials to your photo… {elapsed}s (usually 20–40 s)</p>}
          {error && <p className="notice error" role="alert">{error}</p>}
        </div>
        <aside className="panel">
          <div className="field">
            <label htmlFor="design-pick">Design</label>
            <select id="design-pick" value={design.id} onChange={(e) => onSelectDesign(e.target.value)}>
              {project.designs.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>
          <button type="button" className="btn btn-primary" disabled={busy || left <= 0} aria-busy={busy} onClick={render}>
            {design.renderUrl ? 'Render again' : 'Render this design'}
          </button>
          <p className="badge">{project.renderCount} of {project.renderCap} previews used</p>
          {left <= 0 && <p className="notice warn">All previews for this project are used. You can still get the estimate and report.</p>}
          <button type="button" className="btn" onClick={onNext}>Next: see the cost</button>
        </aside>
      </div>
    </section>
  )
}
```

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: succeeds.

- [ ] **Step 4: Commit**

```bash
cd .. && git add frontend/src && git commit -m "feat: add render preview with before/after slider

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: 05 Estimate step + editable rates

**Files:**
- Create: `frontend/src/components/RateCell.tsx`
- Modify: `frontend/src/steps/EstimateStep.tsx` (replace stub)

**Interfaces:**
- Consumes: `api.estimate`, `api.rates`, `api.overrideRate`, `groupByCategory`, `inr`, `num`, `shortDate`, `useCountUp`.
- Produces: `RateCell { value: number; label: string; onCommit: (v: number) => Promise<void> }`.

- [ ] **Step 1: RateCell**

`frontend/src/components/RateCell.tsx`:
```tsx
import { useEffect, useState } from 'react'

interface Props {
  value: number
  label: string
  onCommit: (value: number) => Promise<void>
}

export default function RateCell({ value, label, onCommit }: Props) {
  const [draft, setDraft] = useState(String(value))
  const [state, setState] = useState<'idle' | 'saving' | 'error'>('idle')

  useEffect(() => setDraft(String(value)), [value])

  async function commit() {
    const next = Number(draft)
    if (!Number.isFinite(next) || next <= 0) {
      setState('error')
      return
    }
    if (next === value) return
    setState('saving')
    try {
      await onCommit(next)
      setState('idle')
    } catch {
      setState('error')
    }
  }

  return (
    <input
      className="rate-input"
      type="number"
      inputMode="decimal"
      min={1}
      step="any"
      aria-label={label}
      aria-invalid={state === 'error'}
      aria-busy={state === 'saving'}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === 'Enter') e.currentTarget.blur()
        if (e.key === 'Escape') {
          setDraft(String(value))
          setState('idle')
        }
      }}
    />
  )
}
```

- [ ] **Step 2: EstimateStep**

`frontend/src/steps/EstimateStep.tsx`:
```tsx
import { useCallback, useEffect, useState } from 'react'
import RateCell from '../components/RateCell'
import { api, errorMessage } from '../lib/api'
import { groupByCategory } from '../lib/estimate'
import { inr, num, shortDate } from '../lib/format'
import { useCountUp } from '../lib/hooks'
import type { Design, Estimate, Project, RateRow } from '../lib/types'

interface Props {
  project: Project
  design: Design
  onNext: () => void
}

const SOURCE_LABEL: Record<RateRow['source'], string> = { web: 'Web', estimated: 'Estimate', override: 'Yours' }

function hostOf(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

export default function EstimateStep({ project, design, onNext }: Props) {
  const [estimate, setEstimate] = useState<Estimate | null>(null)
  const [rates, setRates] = useState<RateRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const total = useCountUp(estimate?.grandTotal ?? 0)

  const load = useCallback(async () => {
    setError(null)
    try {
      // Estimate first: it triggers (and caches) the city rate search the rates call then reuses.
      const e = await api.estimate(design.id)
      setEstimate(e)
      setRates(await api.rates(project.state, project.city, project.id))
    } catch (err) {
      setError(errorMessage(err))
      setEstimate(null)
      setRates([])
    } finally {
      setLoading(false)
    }
  }, [design.id, project.id, project.state, project.city])

  useEffect(() => {
    setLoading(true)
    void load()
  }, [load])

  async function override(materialId: string, change: { materialRate?: number; laborRate?: number }) {
    await api.overrideRate(project.id, materialId, change)
    await load()
  }

  const rateFor = (id: string) => rates.find((r) => r.materialId === id)
  const sources = [...new Set(rates.flatMap((r) => r.sources))]

  return (
    <section aria-labelledby="estimate-h">
      <header className="stage-head">
        <p className="label">05 · Estimate</p>
        <h1 id="estimate-h">What it will cost, line by line.</h1>
        <p className="lede">
          {project.city
            ? `Rates for ${project.city}, ${project.state}. Change any rate your contractor quoted and the totals update.`
            : 'No city set, so average rates are used. Add your city on step 01 for local prices.'}
        </p>
      </header>
      {loading && <p className="progress-line" role="status">Measuring surfaces and looking up local rates…</p>}
      {error && <p className="notice error" role="alert">{error} <button type="button" className="btn btn-small" onClick={() => { setLoading(true); void load() }}>Try again</button></p>}
      {estimate && (
        <div className="stack">
          {estimate.warnings.length > 0 && <div className="notice warn"><ul>{estimate.warnings.map((w) => <li key={w}>{w}</li>)}</ul></div>}
          {estimate.lines.length === 0 ? (
            <p className="notice">This design has no priced materials. Pick materials on step 03.</p>
          ) : (
            <div className="table-scroll">
              <table className="cost-table">
                <thead>
                  <tr>
                    <th scope="col">Item</th>
                    <th scope="col" className="num">Area / length</th>
                    <th scope="col" className="num">Quantity</th>
                    <th scope="col" className="num">Material ₹</th>
                    <th scope="col" className="num">Labour ₹</th>
                    <th scope="col" className="num">Material</th>
                    <th scope="col" className="num">Labour</th>
                    <th scope="col" className="num">Total</th>
                  </tr>
                </thead>
                {groupByCategory(estimate.lines).map((g) => (
                  <tbody key={g.category}>
                    {g.lines.map((line) => {
                      const rate = rateFor(line.materialId)
                      return (
                        <tr key={line.materialId}>
                          <td>
                            <strong>{line.name}</strong>
                            <div className="row">
                              <span className="badge">{line.targets.join(' · ')}</span>
                              <span className={`badge ${line.rateSource}`}>
                                {SOURCE_LABEL[line.rateSource]}{rate?.fetchedAt ? ` · ${shortDate(rate.fetchedAt)}` : ''}
                              </span>
                            </div>
                          </td>
                          <td className="num">{num(line.measure)} {line.rateUnit}</td>
                          <td className="num">{num(line.quantity)} {line.qtyUnit}</td>
                          <td className="num">
                            <RateCell value={line.materialRate} label={`${line.name} material rate per ${line.rateUnit}`}
                              onCommit={(v) => override(line.materialId, { materialRate: v })} />
                          </td>
                          <td className="num">
                            <RateCell value={line.laborRate} label={`${line.name} labour rate per ${line.rateUnit}`}
                              onCommit={(v) => override(line.materialId, { laborRate: v })} />
                          </td>
                          <td className="num">{inr(line.materialCost)}</td>
                          <td className="num">{inr(line.laborCost)}</td>
                          <td className="num">{inr(line.total)}</td>
                        </tr>
                      )
                    })}
                    <tr className="subtotal">
                      <td colSpan={5}>{g.category} subtotal</td>
                      <td className="num">{inr(g.materialCost)}</td>
                      <td className="num">{inr(g.laborCost)}</td>
                      <td className="num">{inr(g.total)}</td>
                    </tr>
                  </tbody>
                ))}
              </table>
            </div>
          )}
          <details>
            <summary>How this was calculated</summary>
            <ul>{estimate.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
            {sources.length > 0 && (
              <>
                <p className="label">Rate sources</p>
                <ul>{sources.map((s) => <li key={s}><a href={s} target="_blank" rel="noreferrer noopener">{hostOf(s)}</a></li>)}</ul>
              </>
            )}
          </details>
          <div className="total-bar">
            <span>Estimated total</span>
            <span className="amount" aria-live="polite">{inr(total)}</span>
          </div>
          <button type="button" className="btn btn-primary" onClick={onNext}>Next: get the report</button>
        </div>
      )}
    </section>
  )
}
```

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: succeeds.

- [ ] **Step 4: Commit**

```bash
cd .. && git add frontend/src && git commit -m "feat: add estimate step with editable city rates

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: 06 Report step

**Files:**
- Modify: `frontend/src/steps/ReportStep.tsx` (replace stub)

**Interfaces:**
- Consumes: `api.reportUrl`.

- [ ] **Step 1: Implement**

`frontend/src/steps/ReportStep.tsx`:
```tsx
import { useState } from 'react'
import { api } from '../lib/api'
import type { Design, Project } from '../lib/types'

interface Props {
  project: Project
  design: Design
}

export default function ReportStep({ project, design }: Props) {
  const [copied, setCopied] = useState<'idle' | 'done' | 'error'>('idle')

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}/?p=${project.id}`)
      setCopied('done')
    } catch {
      setCopied('error')
    }
  }

  return (
    <section aria-labelledby="report-h">
      <header className="stage-head">
        <p className="label">06 · Report</p>
        <h1 id="report-h">Take this to your contractor.</h1>
        <p className="lede">
          The PDF has your original and redesigned photo, the materials for “{design.name}”, the measured areas, quantities and the full cost breakdown.
        </p>
      </header>
      <div className="stack" style={{ maxWidth: '60ch' }}>
        <div className="row">
          <a className="btn btn-primary" href={api.reportUrl(design.id)} download>Download report (PDF)</a>
          <button type="button" className="btn" onClick={copyLink}>
            {copied === 'done' ? 'Link copied' : 'Copy project link'}
          </button>
        </div>
        {copied === 'error' && (
          <p className="notice error" role="alert">Couldn't copy. The link is: {window.location.origin}/?p={project.id}</p>
        )}
        <p className="notice">Anyone with the project link can open and edit this project. Share it only with people you trust.</p>
      </div>
    </section>
  )
}
```

- [ ] **Step 2: Build + tests**

Run: `npm run build && npx vitest run`
Expected: build succeeds; `20 passed`.

- [ ] **Step 3: Commit**

```bash
cd .. && git add frontend/src && git commit -m "feat: add report download step

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Browser walkthrough + Hallmark slop test (controller-run)

Run by the controller in the main session (needs the browser pane, the live backend and Vertex). Requires the sample photos from backend Task 13.

**Files:**
- Create: `.claude/launch.json`
- Modify (only to fix findings): any `frontend/src/**`
- Modify: `.hallmark/log.json` (confirm entry)

- [ ] **Step 1: Launch config**

`.claude/launch.json`:
```json
{
  "version": "0.0.1",
  "configurations": [
    { "name": "backend", "runtimeExecutable": "backend/.venv/Scripts/python.exe", "runtimeArgs": ["backend/manage.py", "runserver", "127.0.0.1:8000"], "port": 8000 },
    { "name": "frontend", "runtimeExecutable": "npm", "runtimeArgs": ["--prefix", "frontend", "run", "dev"], "port": 5173 }
  ]
}
```
Run `python backend/manage.py migrate` first, then `preview_start` both.

- [ ] **Step 2: Walk the flow at 1440 px**

Upload `backend/scripts/samples/house1.jpg` → set city Pune → Find parts → move one corner, add a pillar, save → set scale from the door (7 ft) → Describe: "Grey texture walls, slate on pillars, glass railing" → Preview → Render → slide compare → Estimate: change one material rate, confirm total updates → Report: PDF downloads and opens.
Expected: no console errors (`read_console_messages`), no 500s (`read_network_requests`).

- [ ] **Step 3: Responsive + states**

`resize_window` to 375, 768 and 320. At each: no horizontal page scroll (`document.documentElement.scrollWidth <= innerWidth`), buttons on one line, mobile step bar works, table scrolls inside its box. Check loading, empty (new project), error (stop backend → friendly "Cannot reach the server") and success states.

- [ ] **Step 4: Hallmark slop test**

Load `C:\Users\mihir\.claude\skills\hallmark\references\slop-test.md`; answer every gate for this build; fix failures; record the six pre-emit critique scores as a comment at the top of `frontend/src/styles.css`: `/* Hallmark · pre-emit critique: P_ H_ E_ S_ R_ V_ */`.

- [ ] **Step 5: Commit**

```bash
git add .claude/launch.json frontend .hallmark && git commit -m "chore: verify UI in browser and pass Hallmark slop test

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Self-review

**Spec coverage**

| Spec item | Task |
|---|---|
| M1 upload, guidance, primary pick | 6 |
| M3 review/adjust regions (move corners, move, retype, delete, add) | 7 |
| M4 scale calibration UI | 7 |
| M5 catalog with durability/upkeep shown | 8 (manual picker badge) |
| M6 free text + guided Q&A | 8 |
| M7 per-part materials + edit, multiple designs, switching | 8, 9 (switcher) |
| M8 render + before/after + render cap shown | 9 |
| M11 state → city picker | 6 (reused in Estimate via step 01 prompt) |
| M12 cost breakdown, per-category subtotals, editable rates, recalculation | 10 |
| M13 PDF download | 11 |
| M14 save / reopen by link | 5 (`?p=`), 11 (copy link) |
| UI states: loading / empty / error / success | every step; verified in 12 |
| Mobile 375 px, a11y basics | 1 (CSS), 12 (verification) |

**Placeholder scan:** Task 5 step stubs are intentional scaffolding replaced by Tasks 6–11 (each later task gives full code). No TBD/TODO.

**Type consistency:** step props in Task 5 match each step's `Props` in Tasks 6–11; `api` method names in Task 4 match all call sites; `CategoryGroup` fields match the Estimate table; `RateRow.source` values match `SOURCE_LABEL` keys and `.badge.web/.override` classes.
