import type { Design, Project } from '../lib/types'

interface Props {
  project: Project
  design: Design
}

export default function ReportStep({ design }: Props) {
  return <section><h1>Report for {design.name}</h1></section>
}
