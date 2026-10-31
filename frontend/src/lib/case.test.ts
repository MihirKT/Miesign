import { expect, it } from 'vitest'
import { keysToCamel, keysToSnake } from './case'

const SNAKE = {
  project_id: 'p',
  quad: [[1, 2], [3, 4]],
  designs: [{
    render_url: null,
    spec: { keep_unchanged: ['roof_edge'], assignments: [{ material_id: 'x', target: 'type:roof_edge' }] },
  }],
}
const CAMEL = {
  projectId: 'p',
  quad: [[1, 2], [3, 4]],
  designs: [{
    renderUrl: null,
    spec: { keepUnchanged: ['roof_edge'], assignments: [{ materialId: 'x', target: 'type:roof_edge' }] },
  }],
}

it('converts nested keys both ways and leaves values alone', () => {
  expect(keysToCamel(SNAKE)).toEqual(CAMEL)
  expect(keysToSnake(CAMEL)).toEqual(SNAKE)
})

it('passes FormData and primitives through untouched', () => {
  const form = new FormData()
  expect(keysToSnake(form)).toBe(form)
  expect(keysToCamel(5)).toBe(5)
  expect(keysToCamel(null)).toBeNull()
})
