/**
 * Fluid "magic" overlay drawn over an image while the AI works on it. The blobs take the design's own colours,
 * so the wait previews the palette that is about to appear.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

import type { CSSProperties, ReactNode } from 'react'

const FALLBACK = ['#C8553D', '#E3B35B', '#2F5D62', '#9CAF88']

interface Props {
  active: boolean
  label: string
  seconds?: number
  colors?: (string | null)[]
  children: ReactNode
}

export default function MagicLoader({ active, label, seconds, colors = [], children }: Props) {
  const picked = colors.filter((c): c is string => !!c)
  const palette = [...picked, ...FALLBACK].slice(0, 4)
  return (
    <div className="magic" aria-busy={active}>
      {children}
      {active && (
        <div className="magic-veil" role="status">
          {palette.map((c, i) => <span key={i} className="magic-blob" style={{ '--c': c } as CSSProperties} aria-hidden="true" />)}
          <span className="magic-sheen" aria-hidden="true" />
          <span className="magic-sparks" aria-hidden="true"><i /><i /><i /><i /><i /></span>
          <p className="magic-caption">
            {label}
            {seconds !== undefined && <span className="mono"> {seconds}s</span>}
          </p>
        </div>
      )}
    </div>
  )
}
