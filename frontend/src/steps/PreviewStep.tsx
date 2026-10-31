import type { Design, Project } from '../lib/types'

interface Props {
  project: Project
  design: Design
  onChange: (p: Project) => void
  onSelectDesign: (id: string) => void
  onNext: () => void
}

export default function PreviewStep({ design }: Props) {
  return <section><h1>Preview of {design.name}</h1></section>
}
