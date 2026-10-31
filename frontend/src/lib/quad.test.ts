/**
 * Tests quad building, clamping and moving.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

import { expect, it } from 'vitest'
import { clampPoint, moveCorner, newPartQuad, rectQuad, translateQuad } from './quad'

it('builds and clamps', () => {
  expect(rectQuad(1, 2, 3, 4)).toEqual([[1, 2], [3, 2], [3, 4], [1, 4]])
  expect(clampPoint([-5, 120], 100, 100)).toEqual([0, 100])
})

it('moves one corner inside the image', () => {
  const q = rectQuad(10, 10, 50, 50)
  expect(moveCorner(q, 2, [200, 60], 100, 100)).toEqual([[10, 10], [50, 10], [100, 60], [10, 50]])
})

it('translates the whole quad but keeps it inside', () => {
  const q = rectQuad(10, 10, 50, 50)
  expect(translateQuad(q, 5, -3, 100, 100)).toEqual(rectQuad(15, 7, 55, 47))
  expect(translateQuad(q, 500, -500, 100, 100)).toEqual(rectQuad(60, 0, 100, 40))
})

it('creates a new centred part', () => {
  expect(newPartQuad(1000, 800)).toEqual(rectQuad(425, 340, 575, 460))
})
