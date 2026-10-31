/**
 * Groups estimate lines by category and sums material, labour and total per group.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

import type { EstimateLine } from './types'

export interface CategoryGroup {
  category: string
  lines: EstimateLine[]
  materialCost: number
  laborCost: number
  total: number
}

export function groupByCategory(lines: EstimateLine[]): CategoryGroup[] {
  const groups = new Map<string, CategoryGroup>()
  for (const line of lines) {
    const g = groups.get(line.category) ?? { category: line.category, lines: [], materialCost: 0, laborCost: 0, total: 0 }
    g.lines.push(line)
    g.materialCost += line.materialCost
    g.laborCost += line.laborCost
    g.total += line.total
    groups.set(line.category, g)
  }
  return [...groups.values()]
}
