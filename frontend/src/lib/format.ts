/**
 * Display formatting: INR with Indian digit grouping, measures, part-type labels and short dates.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

const RUPEES = new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR', minimumFractionDigits: 0, maximumFractionDigits: 0,
})
const MEASURE = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 1 })
const SHORT_DATE = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' })

export const inr = (amount: number) => RUPEES.format(amount)
export const num = (value: number) => MEASURE.format(value)

export function typeLabel(type: string): string {
  const words = type.replace(/_/g, ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

export function shortDate(iso: string | null): string {
  return iso ? SHORT_DATE.format(new Date(iso)) : ''
}
