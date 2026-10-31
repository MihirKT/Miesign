import type { Material, Project } from '../lib/types'

interface Props {
  project: Project
  catalog: Material[]
  activeDesignId: string | null
  onChange: (p: Project) => void
  onSelectDesign: (id: string) => void
  onNext: () => void
}

export default function DesignStep({ project }: Props) {
  return <section><h1>Design for {project.name}</h1></section>
}
