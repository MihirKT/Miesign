/**
 * Tests the paint presets and colour naming.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

import { describe, expect, it } from 'vitest'
import { PAINT_PRESETS, colorText } from './palette'

describe('PAINT_PRESETS', () => {
  it('has 8 unique, valid presets', () => {
    expect(PAINT_PRESETS).toHaveLength(8)
    expect(new Set(PAINT_PRESETS.map((p) => p.name)).size).toBe(8)
    for (const p of PAINT_PRESETS) expect(p.hex).toMatch(/^#[0-9A-F]{6}$/)
    // colorText labels presets by name and custom colours by hex
    expect(colorText('#c8553d')).toBe('Terracotta · #C8553D')
    expect(colorText('#123abc')).toBe('#123ABC')
  })
})
