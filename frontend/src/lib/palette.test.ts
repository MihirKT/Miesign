/**
 * Tests the paint shade families and colour naming.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

import { describe, expect, it } from 'vitest'
import { PAINT_PRESETS, SHADE_FAMILIES, colorText, familyOf } from './palette'

describe('PAINT_PRESETS', () => {
  it('has unique, valid shades in every family', () => {
    expect(SHADE_FAMILIES.length).toBeGreaterThanOrEqual(8)
    expect(PAINT_PRESETS.length).toBeGreaterThanOrEqual(45)
    expect(new Set(PAINT_PRESETS.map((p) => p.name.toLowerCase())).size).toBe(PAINT_PRESETS.length)
    expect(new Set(PAINT_PRESETS.map((p) => p.hex)).size).toBe(PAINT_PRESETS.length)
    for (const p of PAINT_PRESETS) expect(p.hex).toMatch(/^#[0-9A-F]{6}$/)
  })

  it('labels presets by name and custom colours by hex', () => {
    expect(colorText('#c8553d')).toBe('Terracotta · #C8553D')
    expect(colorText('#123abc')).toBe('#123ABC')
    expect(familyOf('#2f5d62')?.family).toBe('Blues & teals')
    expect(familyOf('#123abc')).toBeUndefined()
  })
})
