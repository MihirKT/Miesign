/**
 * Tests step unlocking and resume logic.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

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
