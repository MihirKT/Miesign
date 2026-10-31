import type { Project } from '../lib/types'

interface Props {
  project: Project
  onChange: (p: Project) => void
  onNext: () => void
}

export default function PartsStep({ project }: Props) {
  return <section><h1>Parts for {project.name}</h1></section>
}
