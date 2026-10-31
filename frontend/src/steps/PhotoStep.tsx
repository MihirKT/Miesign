import type { Project, StateEntry } from '../lib/types'

interface Props {
  project: Project | null
  states: StateEntry[]
  ensureProject: () => Promise<Project>
  onChange: (p: Project) => void
  onNext: () => void
}

export default function PhotoStep({ onNext }: Props) {
  return <section><h1>Photo</h1><button type="button" onClick={onNext}>Next</button></section>
}
