import type { Design, Project } from '../lib/types'

interface Props {
  project: Project
  design: Design
  onNext: () => void
}

export default function EstimateStep({ design }: Props) {
  return <section><h1>Estimate for {design.name}</h1></section>
}
