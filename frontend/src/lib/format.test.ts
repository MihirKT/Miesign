import { expect, it } from 'vitest'
import { inr, num, shortDate, typeLabel } from './format'

it('formats rupees with Indian grouping and no paise', () => {
  expect(inr(184500)).toBe('₹1,84,500')
  expect(inr(0)).toBe('₹0')
  expect(inr(12345678)).toBe('₹1,23,45,678')
})

it('formats measures to one decimal', () => {
  expect(num(12.345)).toBe('12.3')
  expect(num(1000)).toBe('1,000')
})

it('labels part types', () => {
  expect(typeLabel('roof_edge')).toBe('Roof edge')
  expect(typeLabel('wall')).toBe('Wall')
})

it('formats a short date', () => {
  expect(shortDate('2026-10-31T12:00:00Z')).toBe('31 Oct')
  expect(shortDate(null)).toBe('')
})
