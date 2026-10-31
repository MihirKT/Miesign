import { typeLabel } from '../lib/format'
import { colorText } from '../lib/palette'
import type { Assignment, Material } from '../lib/types'

interface Props {
  assignments: Assignment[]
  catalog: Material[]
  partFirst?: boolean
}

export default function AssignmentList({ assignments, catalog, partFirst = false }: Props) {
  return (
    <ul className="assign-list">
      {assignments.map((a) => {
        const material = catalog.find((m) => m.id === a.materialId)?.name ?? a.materialId
        const part = typeLabel(a.target.split(':')[1] ?? a.target)
        return (
          <li key={`${a.target}-${a.materialId}`}>
            {a.color && <span className="color-chip" style={{ background: a.color }} aria-hidden="true" />}
            <span>
              {partFirst ? `${part} · ${material}` : `${material} on ${part}`}
              {a.color && ` · ${colorText(a.color)}`}
            </span>
          </li>
        )
      })}
    </ul>
  )
}
