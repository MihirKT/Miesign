/**
 * Shared TypeScript types mirroring the API responses.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

export const COMPONENT_TYPES = [
  'wall', 'window', 'door', 'balcony', 'pillar', 'parapet', 'gate', 'roof_edge', 'railing',
] as const
export type ComponentType = (typeof COMPONENT_TYPES)[number]
export type Point = [number, number]
export type Quad = [Point, Point, Point, Point]

export interface Part {
  id?: string
  type: ComponentType
  quad: Quad
  floor: number
  source?: 'ai' | 'user'
  confidence?: number | null
}

export interface Photo {
  id: string
  url: string
  width: number
  height: number
  qualityOk: boolean
  issues: string[]
  tips: string[]
}

export interface Assignment {
  target: string
  materialId: string
  color: string | null
  finish: string
}

export interface DesignSpec {
  style: string
  palette: string[]
  assignments: Assignment[]
  keepUnchanged: ComponentType[]
}

export interface Design {
  id: string
  name: string
  mode: 'free_text' | 'guided' | 'manual'
  input: Record<string, unknown>
  spec: DesignSpec
  rationale: string
  warnings: string[]
  renderUrl: string | null
  createdAt: string
}

export interface Project {
  id: string
  name: string
  state: string
  city: string
  pxPerFt: number | null
  scaleSource: 'default' | 'user'
  primaryPhotoId: string | null
  renderCount: number
  renderCap: number
  photos: Photo[]
  components: Part[]
  designs: Design[]
}

export interface Material {
  id: string
  name: string
  category: string
  appliesTo: ComponentType[]
  rateUnit: 'sqft' | 'rft'
  qtyUnit: string
  wastagePct: number
  baseMaterialRate: number
  baseLaborRate: number
  durabilityYears: string
  maintenance: 'low' | 'medium' | 'high'
  budget: 'low' | 'mid' | 'high'
  climates: string[]
  styles: string[]
}

export interface RateRow {
  materialId: string
  rateUnit: 'sqft' | 'rft'
  materialRate: number
  laborRate: number
  source: 'web' | 'estimated' | 'override'
  sources: string[]
  fetchedAt: string | null
}

export interface EstimateLine {
  category: string
  materialId: string
  name: string
  targets: string[]
  measure: number
  rateUnit: 'sqft' | 'rft'
  quantity: number
  qtyUnit: string
  wastagePct: number
  materialRate: number
  laborRate: number
  rateSource: 'web' | 'estimated' | 'override'
  materialCost: number
  laborCost: number
  total: number
}

export interface Estimate {
  scale: { pxPerFt: number; source: 'default' | 'user' }
  lines: EstimateLine[]
  grandTotal: number
  assumptions: string[]
  warnings: string[]
  location: { state: string; city: string }
}

export interface StateEntry {
  name: string
  cities: { name: string; tier: number }[]
}

export interface Answers {
  budget: 'low' | 'mid' | 'high'
  climate: 'coastal' | 'heavy_rain' | 'hot_dry' | 'moderate'
  style: 'modern' | 'traditional' | 'minimal' | 'luxe'
  maintenance: 'low' | 'medium'
  colorMood: string
  keepUnchanged: ComponentType[]
}
