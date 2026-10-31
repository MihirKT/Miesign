/**
 * Paint shade chooser: pick a colour family, tap a named shade, or open the system picker for any other colour.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

import { useState } from 'react'
import { SHADE_FAMILIES, colorText, familyOf } from '../lib/palette'

// Neutral starting swatch for the system picker; stored only when the user changes it.
const DEFAULT_SWATCH = '#d9d4cc'

interface Props {
  label: string
  value: string | null
  disabled?: boolean
  onChange: (hex: string) => void
}

export default function ShadePicker({ label, value, disabled, onChange }: Props) {
  const [family, setFamily] = useState(() => familyOf(value)?.family ?? SHADE_FAMILIES[0].family)
  const shades = SHADE_FAMILIES.find((f) => f.family === family)?.shades ?? []
  return (
    <div className="shade-picker" role="group" aria-label={`${label} colour`}>
      <div className="family-row" role="tablist" aria-label={`${label} colour families`}>
        {SHADE_FAMILIES.map((f) => (
          <button key={f.family} type="button" role="tab" className="family-tab" aria-selected={f.family === family}
            disabled={disabled} onClick={() => setFamily(f.family)}>
            <span className="family-dot" style={{ background: f.shades[Math.floor(f.shades.length / 2)].hex }} aria-hidden="true" />
            {f.family}
          </button>
        ))}
      </div>
      <div className="swatches">
        {shades.map((s) => (
          <button key={s.hex} type="button" className="swatch-btn" style={{ background: s.hex }} title={s.name}
            aria-label={`Use ${s.name} ${s.hex}`} aria-pressed={value?.toLowerCase() === s.hex.toLowerCase()}
            disabled={disabled} onClick={() => onChange(s.hex)} />
        ))}
        <label className="custom-colour">
          <input type="color" value={value ?? DEFAULT_SWATCH} disabled={disabled} onChange={(e) => onChange(e.target.value)} />
          Any colour
        </label>
      </div>
      {value && <span className="mono">{colorText(value)}</span>}
    </div>
  )
}
