# Limitations

Miesign · Author: Mihir Kapildev Tiwari

Miesign gives an advisory estimate from one photo. Confirm measurements and prices with a contractor before work begins.

## Measurement

- **One visible facade only.** Sides and back of the house are not measured.
- **Perspective distorts areas.** There is no depth information, so a photo taken at an angle makes near parts look larger than far ones, and one scale is applied to the whole photo.
- **The default scale is an assumption.** A 7 ft door, a 4 ft window, or a 20 ft visible front. If none of those match your house, enter one real height on the Parts step.
- **Detection boxes are rectangles.** Real parts are not, so areas are approximations. Gemini can miss parts or draw duplicates. You can edit every box; a fallback wall is added if no wall is found, and walls mostly inside a larger wall are dropped to avoid pricing twice. Overlapping walls are flagged on the estimate.

## Preview

- **The render is generative.** The model can add, remove or alter small elements. In live testing it added an extra railing once. Treat the preview as a guide, not a photograph.
- **Lighting changes perceived colour.** The prompt asks for the exact hex and a swatch card is sent with the photo. On three real phone photos the rendered wall hue was within 2 to 4 degrees of the request and about 70 % of the requested saturation was kept, so a render looks a little duller than the swatch.
- **Eight previews per project.** An unchanged design reuses its saved render; a failed render is refunded.

## Rates

- **Web rates are averages from search, with sanity bounds.** They are not quotes. A value outside 0.3x to 3x of the catalog base is discarded. When search fails, rates are the catalog base adjusted by city tier, labelled "Estimate".
- You can override any rate for your project.

## Product

- **No accounts.** Anyone with the project link can view and edit that project.
- **SQLite and local media on a single instance.** Not built for several servers or heavy traffic.
- **English and INR only.**
