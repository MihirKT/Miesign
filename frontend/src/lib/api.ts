import { keysToCamel, keysToSnake } from './case'
import type { Answers, Design, DesignSpec, Estimate, Material, Part, Project, RateRow, StateEntry } from './types'

const BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')
const FALLBACK = 'Something went wrong. Try again.'

export class ApiError extends Error {
  constructor(message: string, public code: string, public status: number) {
    super(message)
  }
}

export const errorMessage = (e: unknown) => (e instanceof ApiError ? e.message : FALLBACK)

type Query = Record<string, string | undefined>

async function request<T>(method: 'GET' | 'POST', path: string, opts: { query?: Query; body?: unknown; form?: FormData } = {}): Promise<T> {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(opts.query ?? {})) if (v !== undefined) params.set(k, v)
  const qs = params.toString()
  const url = `${BASE}${path}${qs ? `?${qs}` : ''}`
  const init: RequestInit = { method }
  if (opts.form) {
    init.body = opts.form
  } else if (opts.body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' }
    init.body = JSON.stringify(keysToSnake(opts.body))
  }

  let res: Response
  try {
    res = await fetch(url, init)
  } catch {
    throw new ApiError('Cannot reach the server. Check your connection and try again.', 'NETWORK', 0)
  }
  if (!res.ok) {
    let message = FALLBACK
    let code = 'UNKNOWN'
    try {
      const data = await res.json()
      message = data?.error?.message ?? message
      code = data?.error?.code ?? code
    } catch {
      // Non-JSON error page (proxy/gateway); keep the friendly fallback.
    }
    throw new ApiError(message, code, res.status)
  }
  return keysToCamel<T>(await res.json())
}

export const api = {
  createProject: (name?: string) => request<Project>('POST', '/api/project/create', { body: { name } }),
  getProject: (id: string) => request<Project>('GET', '/api/project', { query: { id } }),
  updateProject: (id: string, patch: { name?: string; state?: string; city?: string }) =>
    request<Project>('POST', '/api/project/update', { query: { id }, body: patch }),
  uploadPhoto: (projectId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<Project>('POST', '/api/photo/upload', { query: { project_id: projectId }, form })
  },
  setPrimary: (projectId: string, photoId: string) =>
    request<Project>('POST', '/api/photo/set-primary', { query: { project_id: projectId }, body: { photoId } }),
  detect: (projectId: string) => request<Project>('POST', '/api/structure/detect', { query: { project_id: projectId } }),
  saveParts: (projectId: string, components: Part[]) =>
    request<Project>('POST', '/api/structure/save', { query: { project_id: projectId }, body: { components } }),
  setScale: (projectId: string, input: { componentId: string; realHeightFt: number } | { useDefault: true }) =>
    request<Project>('POST', '/api/scale/set', { query: { project_id: projectId }, body: input }),
  catalog: () => request<{ materials: Material[] }>('GET', '/api/catalog').then((r) => r.materials),
  locations: () => request<{ states: StateEntry[] }>('GET', '/api/locations').then((r) => r.states),
  rates: (state: string, city: string, projectId: string) =>
    request<{ rates: RateRow[] }>('GET', '/api/rates', { query: { state, city, project_id: projectId } }).then((r) => r.rates),
  overrideRate: (projectId: string, materialId: string, rates: { materialRate?: number; laborRate?: number }) =>
    request<{ rates: RateRow[] }>('POST', '/api/rates/override', { query: { project_id: projectId }, body: { materialId, ...rates } })
      .then((r) => r.rates),
  designFromText: (projectId: string, text: string) =>
    request<{ designs: Design[] }>('POST', '/api/design/from-text', { query: { project_id: projectId }, body: { text } })
      .then((r) => r.designs),
  recommend: (projectId: string, answers: Answers) =>
    request<{ designs: Design[] }>('POST', '/api/design/recommend', { query: { project_id: projectId }, body: answers })
      .then((r) => r.designs),
  saveDesign: (projectId: string, design: { id?: string; name: string; spec: DesignSpec }) =>
    request<{ designs: Design[] }>('POST', '/api/design/save', { query: { project_id: projectId }, body: design })
      .then((r) => r.designs[0]),
  render: (designId: string) => request<Design>('POST', '/api/design/render', { query: { id: designId } }),
  estimate: (designId: string) => request<Estimate>('GET', '/api/estimate', { query: { design_id: designId } }),
  reportUrl: (designId: string) => `${BASE}/api/report?design_id=${encodeURIComponent(designId)}`,
}
