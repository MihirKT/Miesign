/**
 * The eight paint presets offered as one-tap swatches, and helpers to name a hex colour.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

export interface PaintPreset { name: string; hex: string }

// Keep in sync with the "exterior paint presets" block in tokens.css and PAINT_PRESETS in backend/core/ai.py:
// the backend resolves a colour named in words to the same hex as the swatch the user taps.
export const PAINT_PRESETS: PaintPreset[] = [
  { name: 'Off-white', hex: '#F3EFE6' },
  { name: 'Cream', hex: '#F3E9DC' },
  { name: 'Sandstone', hex: '#D8C3A5' },
  { name: 'Terracotta', hex: '#C8553D' },
  { name: 'Sage green', hex: '#9CAF88' },
  { name: 'Sky grey', hex: '#A7B4BE' },
  { name: 'Charcoal', hex: '#36454F' },
  { name: 'Deep teal', hex: '#2F5D62' },
]

export const presetFor = (hex: string | null) =>
  hex ? PAINT_PRESETS.find((p) => p.hex.toLowerCase() === hex.toLowerCase()) : undefined

export const colorText = (hex: string) => {
  const preset = presetFor(hex)
  return preset ? `${preset.name} · ${preset.hex}` : hex.toUpperCase()
}
