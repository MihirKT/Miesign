/**
 * Tests category grouping and subtotals.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

import { expect, it } from 'vitest'
import { groupByCategory } from './estimate'
import type { EstimateLine } from './types'

const line = (category: string, materialCost: number, laborCost: number) =>
  ({ category, materialCost, laborCost, total: materialCost + laborCost }) as EstimateLine

it('groups lines by category in first-seen order with subtotals', () => {
  const groups = groupByCategory([line('Paint', 100, 50), line('Railing', 900, 100), line('Paint', 10, 5)])
  expect(groups.map((g) => g.category)).toEqual(['Paint', 'Railing'])
  expect(groups[0]).toMatchObject({ materialCost: 110, laborCost: 55, total: 165 })
  expect(groups[0].lines).toHaveLength(2)
  expect(groups[1].total).toBe(1000)
})
