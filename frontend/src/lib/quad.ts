import type { Point, Quad } from './types'

// New parts start as a box this fraction of the photo's width/height.
const NEW_PART_FRACTION = 0.15

export const rectQuad = (x0: number, y0: number, x1: number, y1: number): Quad => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

export function clampPoint([x, y]: Point, width: number, height: number): Point {
  return [Math.min(Math.max(x, 0), width), Math.min(Math.max(y, 0), height)]
}

export function moveCorner(quad: Quad, index: number, point: Point, width: number, height: number): Quad {
  return quad.map((p, i) => (i === index ? clampPoint(point, width, height) : p)) as Quad
}

export function translateQuad(quad: Quad, dx: number, dy: number, width: number, height: number): Quad {
  const xs = quad.map((p) => p[0])
  const ys = quad.map((p) => p[1])
  const sx = Math.min(Math.max(dx, -Math.min(...xs)), width - Math.max(...xs))
  const sy = Math.min(Math.max(dy, -Math.min(...ys)), height - Math.max(...ys))
  return quad.map(([x, y]) => [x + sx, y + sy]) as Quad
}

export function newPartQuad(width: number, height: number): Quad {
  const w = width * NEW_PART_FRACTION
  const h = height * NEW_PART_FRACTION
  return rectQuad(width / 2 - w / 2, height / 2 - h / 2, width / 2 + w / 2, height / 2 + h / 2)
}
