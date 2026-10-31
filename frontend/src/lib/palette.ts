/**
 * Exterior paint shades grouped by colour family, offered as one-tap swatches, and helpers to name a hex colour.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

export interface PaintPreset { name: string; hex: string }
export interface ShadeFamily { family: string; shades: PaintPreset[] }

// Keep in sync with PAINT_PRESETS in backend/core/ai.py (a backend test compares them): the backend resolves
// a colour named in words to the same hex as the swatch the user taps.
export const SHADE_FAMILIES: ShadeFamily[] = [
  { family: 'Whites & creams', shades: [
    { name: 'Off-white', hex: '#F3EFE6' }, { name: 'Cream', hex: '#F3E9DC' }, { name: 'Ivory', hex: '#F6F1E1' },
    { name: 'Pearl white', hex: '#F8F6F0' }, { name: 'Linen', hex: '#EDE4D3' }, { name: 'Magnolia', hex: '#F2E8D7' },
  ] },
  { family: 'Beige & sand', shades: [
    { name: 'Sandstone', hex: '#D8C3A5' }, { name: 'Biscuit', hex: '#E3CBA5' }, { name: 'Desert sand', hex: '#E1C699' },
    { name: 'Khaki', hex: '#C3B091' }, { name: 'Mushroom', hex: '#BBA99A' }, { name: 'Taupe', hex: '#A89A8A' },
  ] },
  { family: 'Yellows & ochres', shades: [
    { name: 'Lemon chiffon', hex: '#F2E6A7' }, { name: 'Butter yellow', hex: '#F3DD8C' }, { name: 'Honey', hex: '#E3B35B' },
    { name: 'Turmeric', hex: '#E0A526' }, { name: 'Mustard', hex: '#D4A33B' }, { name: 'Ochre', hex: '#C68A2E' },
  ] },
  { family: 'Reds & terracotta', shades: [
    { name: 'Peach', hex: '#F2C1A0' }, { name: 'Coral', hex: '#E07A5F' }, { name: 'Burnt orange', hex: '#CC6A2C' },
    { name: 'Terracotta', hex: '#C8553D' }, { name: 'Rust', hex: '#A8502E' }, { name: 'Brick red', hex: '#9C3B2E' },
    { name: 'Maroon', hex: '#6E2A2A' },
  ] },
  { family: 'Pinks & purples', shades: [
    { name: 'Blush pink', hex: '#E8C4C0' }, { name: 'Salmon', hex: '#E59A84' }, { name: 'Dusty rose', hex: '#C4918A' },
    { name: 'Lavender', hex: '#C6B8D6' }, { name: 'Mauve', hex: '#9C7F94' },
  ] },
  { family: 'Greens', shades: [
    { name: 'Mint', hex: '#BFD8C2' }, { name: 'Pistachio', hex: '#C2D3A0' }, { name: 'Sage green', hex: '#9CAF88' },
    { name: 'Olive', hex: '#7A7A45' }, { name: 'Moss', hex: '#66784A' }, { name: 'Forest green', hex: '#2F4F3A' },
  ] },
  { family: 'Blues & teals', shades: [
    { name: 'Powder blue', hex: '#B7CCDA' }, { name: 'Aqua', hex: '#8CC7C1' }, { name: 'Sky blue', hex: '#8FB8D8' },
    { name: 'Teal blue', hex: '#3E7C8C' }, { name: 'Deep teal', hex: '#2F5D62' }, { name: 'Denim', hex: '#4F6D8A' },
    { name: 'Navy', hex: '#24344D' },
  ] },
  { family: 'Greys, browns & darks', shades: [
    { name: 'Light grey', hex: '#C9C9C6' }, { name: 'Sky grey', hex: '#A7B4BE' }, { name: 'Dove grey', hex: '#A9A8A4' },
    { name: 'Slate grey', hex: '#6B7378' }, { name: 'Charcoal', hex: '#36454F' }, { name: 'Graphite', hex: '#3A3A3C' },
    { name: 'Walnut', hex: '#6B4A35' }, { name: 'Chocolate brown', hex: '#4E3428' }, { name: 'Jet black', hex: '#1E1E1E' },
  ] },
]

export const PAINT_PRESETS: PaintPreset[] = SHADE_FAMILIES.flatMap((f) => f.shades)

export const presetFor = (hex: string | null) =>
  hex ? PAINT_PRESETS.find((p) => p.hex.toLowerCase() === hex.toLowerCase()) : undefined

export const familyOf = (hex: string | null) =>
  hex ? SHADE_FAMILIES.find((f) => f.shades.some((s) => s.hex.toLowerCase() === hex.toLowerCase())) : undefined

export const colorText = (hex: string) => {
  const preset = presetFor(hex)
  return preset ? `${preset.name} · ${preset.hex}` : hex.toUpperCase()
}
