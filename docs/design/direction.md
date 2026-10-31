# Design Direction — Hallmark

**Inferred context** (user said "go ahead"):
- **Audience**: Indian homeowners aged 30–55, not technical, mostly on phones, worried about cost and getting cheated by contractors. E2M graders second.
- **Use case**: leave with a redesign + a cost estimate trusted enough to take to a contractor.
- **Tone**: utilitarian — a calm reference tool with exact numbers.

## Picks

- **Genre** · editorial (no AI-tool/SaaS/playful signal strong enough; the content is a reference document about one house)
- **Macrostructure** · 14 Narrative Workflow, adapted to an app wizard — six real, ordinal stages: `01 Photo · 02 Parts · 03 Design · 04 Preview · 05 Estimate · 06 Report`. Numbering is genuinely ordinal, so stage labels are allowed (stacked above the heading, never hanging left).
- **Theme** · Almanac (light cool paper · roman serif display · warm brick accent · mono labels · tabular numbers · dense)
- **Nav** · N3 Side-rail (desktop) → single-line "Step 2 of 6 · Parts" bar + thin progress rule (mobile)
- **Footer** · Ft2 Inline single line (disclaimer + project link)
- **Enrichment** · none — the user's own house photo is the only image
- **Motion** · step crossfade · number-tick on totals · region highlight on hover/focus (≤ 3 primitives, Almanac 0.85× durations)
- **Dark mode** · skipped (YAGNI for a 48 h prototype; add when asked)
- **Slop test** · run after build

## Tokens (`frontend/src/tokens.css`)

```css
/* Hallmark · macrostructure: Narrative Workflow · nav: N3 Side-rail · footer: Ft2 Inline
 * theme: Almanac · tone: utilitarian · anchor hue: 38 (brick) · enrichment: none
 */
@import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Newsreader:opsz,wght@6..72,500;6..72,600&display=swap");

:root {
  /* paper & ink — cool, never pure white/black */
  --color-paper:   oklch(97.5% 0.006 240);
  --color-paper-2: oklch(94.5% 0.008 240);
  --color-paper-3: oklch(91% 0.010 240);
  --color-rule:    oklch(86% 0.010 240);
  --color-ink:     oklch(24% 0.020 250);
  --color-ink-2:   oklch(40% 0.018 250);
  --color-ink-3:   oklch(50% 0.014 250);

  /* accent — brick, < 5 % of any viewport */
  --color-accent:      oklch(52% 0.150 38);
  --color-accent-ink:  oklch(98% 0.010 60);
  --color-accent-wash: oklch(94% 0.030 45);

  /* status */
  --color-ok:    oklch(50% 0.120 150);
  --color-warn:  oklch(58% 0.130 75);
  --color-error: oklch(50% 0.170 25);
  --color-focus: oklch(52% 0.170 250);

  /* canvas region strokes — distinct hues, same lightness */
  --region-wall:     oklch(62% 0.14 38);
  --region-window:   oklch(62% 0.14 230);
  --region-door:     oklch(62% 0.14 280);
  --region-balcony:  oklch(62% 0.14 150);
  --region-pillar:   oklch(62% 0.14 85);
  --region-parapet:  oklch(62% 0.14 330);
  --region-gate:     oklch(62% 0.14 190);
  --region-roof_edge:oklch(62% 0.14 0);
  --region-railing:  oklch(62% 0.14 120);

  /* type */
  --font-display: "Newsreader", ui-serif, Georgia, serif;
  --font-body:    "IBM Plex Sans", ui-sans-serif, sans-serif;
  --font-mono:    "IBM Plex Mono", ui-monospace, monospace;
  --text-xs: 0.75rem; --text-sm: 0.875rem; --text-base: 1rem; --text-lg: 1.125rem;
  --text-xl: 1.375rem; --text-2xl: 1.75rem; --text-3xl: 2.25rem;

  /* 4-pt space */
  --space-2xs: 4px; --space-xs: 8px; --space-sm: 12px; --space-md: 16px;
  --space-lg: 24px; --space-xl: 32px; --space-2xl: 48px; --space-3xl: 64px;

  --radius-sm: 4px; --radius-md: 6px;
  --rule-hair: 1px solid var(--color-rule);
  --rule-thick: 2px solid var(--color-ink);

  /* motion — Almanac 0.85× */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in: cubic-bezier(0.7, 0, 0.84, 0);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --dur-fast: 120ms; --dur-base: 200ms; --dur-slow: 320ms;
}
```

## Layout

- **Desktop ≥ 1024 px**: 220 px side-rail (stages `01`–`06` in mono, current = ink + 2 px brick bar, done = ✓ ok-green, locked = ink-3) · workspace (photo / canvas, max 880 px) · 320 px inspector on Parts/Design/Estimate.
- **Tablet 768**: rail collapses to icon-less numbered list at top; inspector stacks under canvas.
- **Mobile 375**: "Step 2 of 6 · Parts" one-line bar + 2 px progress rule; canvas full width; inspector below; primary action pinned at bottom (44 px min). Estimate: grand total pinned at bottom.
- Hairline rules divide panels — no card-in-card, no shadows beyond one `0 1px 0` on the pinned bar.

## Components & voice

| Element | Treatment |
|---|---|
| Stage heading | mono label `02 · PARTS` stacked above Newsreader 600 heading, ≤ 7 words: "Check what we found on your house." |
| Primary button | brick fill, accent-ink text, radius-sm, verb-first: "Find parts", "Render this design", "Download report" |
| Secondary | outlined ink-2 hairline |
| Region list | type colour swatch · type name · sqft in mono, tabular, right-aligned |
| Material card | name, ₹/unit in mono, two plain facts: "Lasts 15+ yrs · Low upkeep" |
| Rate badge | mono xs: `WEB · 31 OCT · 3 sources` (ok) / `ESTIMATE · TIER 2` (ink-3) |
| Cost table | mono tabular numbers, right-aligned, ₹ with Indian grouping (`₹1,84,500`), editable cells underline on hover, focus ring |
| Errors | what happened + what to do: "Photo is too dark. Take it in daylight, facing the house." |
| Empty | "No parts yet. Draw one: tap + then drag on the photo." |
| Loading (AI) | stage-specific line + elapsed seconds, no spinner-only states |

States: every interactive element ships default · hover · focus-visible · active · disabled · loading · error · success. `prefers-reduced-motion` collapses motion to ≤ 150 ms opacity.

## Honest copy

No invented metrics or testimonials anywhere. All money is computed; all rates show their source.
