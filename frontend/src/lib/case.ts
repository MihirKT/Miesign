const toCamel = (key: string) => key.replace(/_([a-z0-9])/g, (_, c: string) => c.toUpperCase())
const toSnake = (key: string) => key.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`)

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && Object.getPrototypeOf(value) === Object.prototype
}

function convert(value: unknown, rename: (key: string) => string): unknown {
  if (Array.isArray(value)) return value.map((v) => convert(v, rename))
  if (isPlainObject(value)) {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [rename(k), convert(v, rename)]))
  }
  return value
}

export function keysToCamel<T>(value: unknown): T {
  return convert(value, toCamel) as T
}

export function keysToSnake(value: unknown): unknown {
  return convert(value, toSnake)
}
