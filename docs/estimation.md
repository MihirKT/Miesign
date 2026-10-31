# Estimation

Miesign · Author: Mihir Kapildev Tiwari

All maths lives in `backend/core/estimation.py` and `backend/core/managers/rates.py`. Gemini supplies boxes and, at most, rate numbers; it never computes an area or a cost.

## 1. Boxes become quads

Detection returns `box_2d = [ymin, xmin, ymax, xmax]` on a 0-1000 grid. Each value is clamped to 0-1000 and scaled by the stored photo's width and height into pixels, giving a four-point quad `[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]`. Quads the user edits are stored the same way, clamped to the image.

## 2. Scale (pixels per foot)

Priority:

1. **User height.** `px_per_ft = part height in px / real height in ft`, from one part the user measured (1 to 100 ft).
2. **Default.** Mean door height in px / 7 ft; else mean window height in px / 4 ft; else image height / 20 ft (assumed visible facade height).

The default is recomputed whenever parts change, until the user sets a real measurement.

## 3. Areas

- Area in px is the shoelace formula on the quad; `area_sqft = area_px / px_per_ft^2`.
- **Wall:** area minus the area of every window and door whose centre lies inside the wall (never below 0).
- **Pillar:** area x 4, since only one face shows and pillars are treated as square columns.
- **Railing** (rate unit rft): running length = quad width in px / `px_per_ft`.
- Other parts (balcony, parapet, gate, roof edge): area as drawn.
- Windows and doors are never priced.

Measures of the same material across parts are summed, then rounded to 0.1.

## 4. Quantities

`factor = 1 + wastage_pct / 100`

| Unit | Formula |
|---|---|
| `L` or `kg` (paint, texture) | `measure x coats / coverage_per_unit x factor`, 1 decimal |
| `pcs` (tiles, panels) | `ceil(measure / piece_sqft x factor)` |
| `sqft`, `rft` | `measure x factor`, 1 decimal |

## 5. Cost

```
material_cost = measure x (1 + wastage) x material_rate
labour_cost   = measure x labour_rate
line_total    = material_cost + labour_cost      (each rounded to a rupee)
```

Wastage applies to material only, not labour. Lines are grouped by catalog category (Paint, Railing, ...) with a subtotal each; the grand total is the sum of line totals.

## 6. Rates, in priority order

1. **Project override** (user-entered material and/or labour rate): always wins.
2. **Cached web rate** for the city, up to 30 days old (`RATE_CACHE_DAYS`).
3. **Gemini grounded Google search** for materials with no usable cache row in that city. A result is accepted only if both rates are within 0.3x to 3x of the catalog base rate; its source URLs are kept.
4. **Tier estimate:** base rate x tier multiplier: tier 1 cities 1.2, tier 2 cities 1.0, tier 3 cities 0.85.

Rows from step 3 are stored as `web`; rows from step 4 as `estimated`. Estimated rows are cached for only 24 hours (`RATE_ESTIMATE_CACHE_HOURS`), so the search is retried soon after a failure. Overrides are per project and are applied after the cache lookup.

## Worked example

From `backend/core/tests/test_estimate.py`. Scale 10 px/ft. Paint: material 15 and labour 10 per sqft, 5 % wastage, 2 coats, 110 sqft per litre. Wall box 100 x 100 px, one window 20 x 20 px inside it, one pillar 10 x 100 px.

- Wall: 100 x 100 px = 10,000 px² / 10² = 100 sqft. Window: 20 x 20 = 400 px² / 100 = 4 sqft. Net wall = 100 - 4 = **96 sqft**.
- Pillar: 10 x 100 = 1,000 px² / 100 = 10 sqft, x 4 faces = **40 sqft**.
- Paint measure = 96 + 40 = **136 sqft**.
- Material = 136 x 1.05 x 15 = 142.8 x 15 = **Rs 2,142**.
- Labour = 136 x 10 = **Rs 1,360**.
- Paint line total = 2,142 + 1,360 = **Rs 3,502**.
- Paint quantity = 136 x 2 / 110 x 1.05 = 2.596, shown as **2.6 L**.

Railing in the same test: box 50 x 10 px, rft unit, so length = 50 / 10 = 5 rft. With override rates 1,000 material and 200 labour and 5 % wastage: material = 5 x 1.05 x 1,000 = Rs 5,250; labour = 5 x 200 = Rs 1,000; total Rs 6,250. Grand total = 3,502 + 6,250 = **Rs 9,752**.
