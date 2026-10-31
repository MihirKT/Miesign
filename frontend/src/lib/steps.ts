/**
 * The six workflow steps, which of them are unlocked for a project, and which one to resume at.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

import type { Project } from './types'

export const STEPS = [
  { key: 'photo', label: 'Photo' },
  { key: 'parts', label: 'Parts' },
  { key: 'design', label: 'Design' },
  { key: 'preview', label: 'Preview' },
  { key: 'estimate', label: 'Estimate' },
  { key: 'report', label: 'Report' },
] as const
export type StepKey = (typeof STEPS)[number]['key']

export function unlockedSteps(project: Project | null): Set<StepKey> {
  const open = new Set<StepKey>(['photo'])
  if (!project?.primaryPhotoId) return open
  open.add('parts')
  if (project.components.length > 0) open.add('design')
  if (project.designs.length > 0) {
    open.add('preview')
    open.add('estimate')
    open.add('report')
  }
  return open
}

export function resumeStep(project: Project): StepKey {
  const open = unlockedSteps(project)
  if (open.has('design')) return 'design'
  if (open.has('parts')) return 'parts'
  return 'photo'
}
