/**
 * Step 03: create a design by describing it, answering guided questions, or picking materials by hand.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

import { useMemo, useState } from 'react'
import { api, errorMessage } from '../lib/api'
import AssignmentList from '../components/AssignmentList'
import ShadePicker from '../components/ShadePicker'
import { typeLabel } from '../lib/format'
import { PAINT_PRESETS, colorText } from '../lib/palette'
import { useElapsed } from '../lib/hooks'
import type { Answers, Assignment, ComponentType, Design, DesignSpec, Material, Project } from '../lib/types'

type Tab = 'describe' | 'guided' | 'manual'
const PAINT_COUNT = PAINT_PRESETS.length
type Pick = { materialId: string; color: string | null }

const EXAMPLES = [
  { label: 'Terracotta and cream', text: 'Terracotta walls, cream parapet, black railing' },
  { label: 'Sage and wood', text: 'Sage green walls, wooden panels on the balcony, steel railing' },
  { label: 'Charcoal modern', text: 'Charcoal ACP panels, white pillars, glass railing' },
  { label: 'Kerala tropical', text: 'Kerala style: ivory walls, brick red cladding on pillars, wood-look panels on the balcony' },
  { label: 'Rajasthani haveli', text: 'Rajasthani haveli look: sandstone cladding, ochre walls, maroon accents, black metal railing' },
  { label: 'Mediterranean', text: 'Mediterranean villa: pearl white texture walls, terracotta parapet, powder blue gate' },
  { label: 'Japandi calm', text: 'Japandi: mushroom beige walls, walnut wood panels, slim charcoal railing' },
  { label: 'Art Deco', text: 'Art Deco: cream walls, deep teal bands on the parapet, black metal railing' },
]
const CHOICES = {
  budget: [['low', 'Tight'], ['mid', 'Balanced'], ['high', 'Premium']],
  climate: [['moderate', 'Moderate'], ['heavy_rain', 'Heavy rain'], ['coastal', 'Coastal'], ['hot_dry', 'Hot and dry']],
  style: [
    ['modern', 'Modern'], ['contemporary', 'Contemporary'], ['minimal', 'Minimal'], ['traditional', 'Traditional Indian'],
    ['kerala', 'Kerala tropical'], ['rajasthani', 'Rajasthani haveli'], ['colonial', 'Colonial'], ['mediterranean', 'Mediterranean'],
    ['scandinavian', 'Scandinavian'], ['japandi', 'Japandi / zen'], ['industrial', 'Industrial'], ['farmhouse', 'Farmhouse rustic'],
    ['art_deco', 'Art Deco'], ['luxe', 'Luxe'],
  ],
  maintenance: [['low', 'Low upkeep'], ['medium', 'Some upkeep is fine']],
} as const
const MODE_LABEL: Record<Design['mode'], string> = { free_text: 'From your words', guided: 'Suggested', manual: 'Picked by you' }

interface Props {
  project: Project
  catalog: Material[]
  activeDesignId: string | null
  onChange: (p: Project) => void
  onSelectDesign: (id: string) => void
  onNext: () => void
}

export default function DesignStep({ project, catalog, activeDesignId, onChange, onSelectDesign, onNext }: Props) {
  const [tab, setTab] = useState<Tab>('describe')
  const [text, setText] = useState('')
  const [answers, setAnswers] = useState<Answers>({
    budget: 'mid', climate: 'moderate', style: 'modern', maintenance: 'low', colorMood: '', keepUnchanged: [],
  })
  const [picks, setPicks] = useState<Partial<Record<ComponentType, Pick>>>({})
  const [editing, setEditing] = useState<Design | null>(null)
  const [busy, setBusy] = useState(false)
  const [enhancing, setEnhancing] = useState(false)
  const [beforeEnhance, setBeforeEnhance] = useState<string | null>(null)
  const [browseShade, setBrowseShade] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState<string | null>(null)
  const elapsed = useElapsed(busy || enhancing)

  async function enhance() {
    if (enhancing || busy) return
    setEnhancing(true)
    setError(null)
    setDone(null)
    try {
      const better = await api.enhanceText(project.id, text)
      setBeforeEnhance(text)
      setText(better)
      setDone('Idea enhanced. Edit it if you like, then create the design.')
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setEnhancing(false)
    }
  }

  function addShade(hex: string) {
    const name = colorText(hex)
    setBrowseShade(hex)
    setText((t) => (t.trim() ? `${t.trim().replace(/[.,]$/, '')}, ${name}` : name))
  }

  const byId = useMemo(() => new Map(catalog.map((m) => [m.id, m])), [catalog])
  const present = useMemo(
    () => [...new Set(project.components.map((c) => c.type))].filter((t) => t !== 'window' && t !== 'door'),
    [project.components],
  )

  async function create(action: () => Promise<Design[]>, success: (created: Design[]) => string) {
    if (busy) return
    setBusy(true)
    setError(null)
    setDone(null)
    try {
      const created = await action()
      const ids = new Set(created.map((d) => d.id))
      onChange({ ...project, designs: [...created, ...project.designs.filter((d) => !ids.has(d.id))] })
      onSelectDesign(created[0].id)
      setDone(success(created))
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const typeOf = (a: Assignment) => (a.target.startsWith('type:') ? a.target.slice(5) : null)
  // Shown = the manual UI can represent it: a type:* target on a present type with a known, applicable material.
  const isShown = (a: Assignment) => {
    const t = typeOf(a)
    const m = byId.get(a.materialId)
    return t !== null && (present as string[]).includes(t) && !!m && m.appliesTo.includes(t as ComponentType)
  }
  const hiddenCount = editing ? editing.spec.assignments.filter((a) => !isShown(a)).length : 0

  function manualSpec(): DesignSpec {
    const fresh = (kept: Assignment[], old: Assignment[]) => [
      ...kept,
      ...(Object.entries(picks) as [ComponentType, Pick | undefined][])
        .filter(([, p]) => p?.materialId)
        .map(([type, p]) => ({
          target: `type:${type}`,
          materialId: p?.materialId ?? '',
          color: p?.color ?? null,
          finish: old.find((a) => a.target === `type:${type}` && a.materialId === p?.materialId)?.finish ?? '',
        })),
    ]
    if (!editing) return { style: '', palette: [], assignments: fresh([], []), keepUnchanged: [] }
    const { spec } = editing
    const kept = spec.assignments.filter((a) => {
      if (isShown(a)) return false
      const t = typeOf(a)
      // An unusable material on a shown type stays unless the user picks something for that type.
      return !(t !== null && (present as string[]).includes(t) && picks[t as ComponentType])
    })
    return { ...spec, assignments: fresh(kept, spec.assignments) }
  }

  function startEdit(d: Design) {
    const next: Partial<Record<ComponentType, Pick>> = {}
    for (const a of d.spec.assignments) {
      if (isShown(a)) next[a.target.slice(5) as ComponentType] = { materialId: a.materialId, color: a.color }
    }
    setPicks(next)
    setEditing(d)
    setTab('manual')
  }

  return (
    <section aria-labelledby="design-h">
      <header className="stage-head">
        <p className="label">03 · Design</p>
        <h1 id="design-h">Choose what goes where.</h1>
        <p className="lede">Describe it in your words, answer a few questions, or pick each material yourself.</p>
      </header>
      <div className="workspace">
        <div className="stack">
          <div className="tabs" role="tablist" aria-label="Ways to design">
            {(['describe', 'guided', 'manual'] as const).map((t) => (
              <button key={t} type="button" role="tab" className="tab" aria-selected={tab === t} onClick={() => { setTab(t); setDone(null) }}>
                {t === 'describe' ? 'Describe it' : t === 'guided' ? 'Help me choose' : 'Pick materials'}
              </button>
            ))}
          </div>

          {tab === 'describe' && (
            <fieldset className="stack plain-fieldset" role="tabpanel" disabled={busy || enhancing}>
              <div className="field">
                <label htmlFor="design-text">What should the house look like?</label>
                <div className={enhancing ? 'enhance-wrap is-enhancing' : 'enhance-wrap'}>
                  <textarea id="design-text" maxLength={1000} value={text} placeholder="e.g. warm earthy walls, wooden balcony, black railing"
                    onChange={(e) => { setText(e.target.value); setBeforeEnhance(null) }} />
                </div>
                <div className="row">
                  <button type="button" className="btn btn-small btn-enhance" disabled={enhancing || busy || text.trim().length < 3}
                    aria-busy={enhancing} onClick={enhance}>
                    <span aria-hidden="true">✦</span> {enhancing ? `Enhancing… ${elapsed}s` : 'Enhance my idea'}
                  </button>
                  {beforeEnhance !== null && (
                    <button type="button" className="btn btn-small" onClick={() => { setText(beforeEnhance); setBeforeEnhance(null); setDone(null) }}>
                      Undo
                    </button>
                  )}
                </div>
              </div>
              <div className="field">
                <span className="field-label">Start from a style</span>
                <div className="chips" aria-label="Examples">
                  {EXAMPLES.map((ex) => (
                    <button key={ex.label} type="button" className="chip" onClick={() => { setText(ex.text); setBeforeEnhance(null) }}>{ex.label}</button>
                  ))}
                </div>
              </div>
              <details className="shade-browser">
                <summary>Browse {PAINT_COUNT} paint shades</summary>
                <p className="lede">Tap a shade to add its name to your description.</p>
                <ShadePicker label="Description" value={browseShade} onChange={addShade} />
              </details>
              <button type="button" className="btn btn-primary" disabled={busy || enhancing || text.trim().length < 3} aria-busy={busy}
                onClick={() => create(() => api.designFromText(project.id, text), () => 'Design created.')}>
                {busy ? `Reading your request… ${elapsed}s` : 'Create design'}
              </button>
            </fieldset>
          )}

          {tab === 'guided' && (
            <fieldset className="stack plain-fieldset" role="tabpanel" disabled={busy}>
              {(Object.keys(CHOICES) as (keyof typeof CHOICES)[]).map((key) => (
                <div key={key} className="field" role="group" aria-labelledby={`q-${key}`}>
                  <span id={`q-${key}`} className="field-label">{typeLabel(key)}</span>
                  <div className="chips">
                    {CHOICES[key].map(([value, label]) => (
                      <button key={value} type="button" className="chip" aria-pressed={answers[key] === value}
                        onClick={() => setAnswers((a) => ({ ...a, [key]: value }))}>{label}</button>
                    ))}
                  </div>
                </div>
              ))}
              <div className="field">
                <label htmlFor="mood">Colour mood (optional)</label>
                <input id="mood" type="text" maxLength={60} placeholder="warm earthy tones" value={answers.colorMood}
                  onChange={(e) => setAnswers((a) => ({ ...a, colorMood: e.target.value }))} />
              </div>
              {present.length > 0 && <div className="field" role="group" aria-labelledby="q-keep">
                <span id="q-keep" className="field-label">Leave these as they are</span>
                <div className="chips">
                  {present.map((t) => (
                    <button key={t} type="button" className="chip" aria-pressed={answers.keepUnchanged.includes(t)}
                      onClick={() => setAnswers((a) => ({
                        ...a,
                        keepUnchanged: a.keepUnchanged.includes(t) ? a.keepUnchanged.filter((x) => x !== t) : [...a.keepUnchanged, t],
                      }))}>{typeLabel(t)}</button>
                  ))}
                </div>
              </div>}
              <button type="button" className="btn btn-primary" disabled={busy} aria-busy={busy}
                onClick={() => create(() => api.recommend(project.id, answers), (c) => `${c.length} design${c.length === 1 ? '' : 's'} suggested.`)}>
                {busy ? `Putting options together… ${elapsed}s` : 'Suggest 3 designs'}
              </button>
            </fieldset>
          )}

          {tab === 'manual' && (
            <fieldset className="stack plain-fieldset" role="tabpanel" disabled={busy}>
              {catalog.length === 0 && <p className="notice">Materials couldn't load. Reload the page.</p>}
              {present.length === 0 && <p className="notice">No paintable parts yet. Go back to step 02.</p>}
              {editing && (
                <div className="notice">
                  <p>Editing “{editing.name}”. Saving updates it.</p>
                  {hiddenCount > 0 && (
                    <p>{hiddenCount} item(s) from the original design (single-part materials or windows/doors) are kept as they are.</p>
                  )}
                  <button type="button" className="btn btn-small" onClick={() => { setEditing(null); setPicks({}) }}>Start a new design</button>
                </div>
              )}
              {present.map((t) => {
                const options = catalog.filter((m) => m.appliesTo.includes(t))
                const pick = picks[t]
                const chosen = pick ? byId.get(pick.materialId) : undefined
                return (
                  <div key={t} className="field">
                    <label htmlFor={`m-${t}`}>{typeLabel(t)}</label>
                    <select id={`m-${t}`} value={pick?.materialId ?? ''}
                      onChange={(e) => setPicks((p) => ({ ...p, [t]: { materialId: e.target.value, color: p[t]?.color ?? null } }))}>
                      <option value="">Leave as it is</option>
                      {options.map((m) => <option key={m.id} value={m.id}>{`${m.name} · ${m.durabilityYears} yrs · ${m.maintenance} upkeep`}</option>)}
                    </select>
                    {pick?.materialId && (
                      <ShadePicker label={typeLabel(t)} value={pick.color}
                        onChange={(hex) => setPicks((p) => ({ ...p, [t]: { materialId: p[t]?.materialId ?? '', color: hex } }))} />
                    )}
                    {chosen && <span className="badge">Lasts {chosen.durabilityYears} yrs · {chosen.maintenance} upkeep</span>}
                  </div>
                )
              })}
              <button type="button" className="btn btn-primary" disabled={busy || manualSpec().assignments.length === 0} aria-busy={busy}
                onClick={() => create(async () => {
                  const saved = await api.saveDesign(project.id, { id: editing?.id, name: editing?.name ?? 'My design', spec: manualSpec() })
                  if (editing) setEditing(saved)
                  return [saved]
                }, () => 'Design saved.')}>
                {editing ? 'Update design' : 'Save design'}
              </button>
            </fieldset>
          )}
          <p role="status" aria-live="polite" className={done ? 'notice ok' : undefined}>{done}</p>
          {error && <p className="notice error" role="alert">{error}</p>}
        </div>

        <aside className="panel">
          <h2>Your designs</h2>
          {project.designs.length === 0 ? (
            <p className="notice">No designs yet. Describe one, ask for suggestions, or pick materials to create your first.</p>
          ) : (
            <div className="design-list">
              {project.designs.map((d) => (
                <article key={d.id} className="design" data-active={d.id === activeDesignId} aria-current={d.id === activeDesignId ? 'true' : undefined}>
                  <span className="badge">{MODE_LABEL[d.mode]}</span>
                  {d.id === activeDesignId && <span className="badge web">In use</span>}
                  <h3>{d.name}</h3>
                  {d.spec.assignments.length > 0
                    ? <AssignmentList assignments={d.spec.assignments} catalog={catalog} />
                    : <p className="lede">No materials applied.</p>}
                  {d.rationale && <p>{d.rationale}</p>}
                  {d.warnings.length > 0 && <div className="notice warn"><ul>{d.warnings.map((w) => <li key={w}>{w}</li>)}</ul></div>}
                  <div className="row">
                    <button type="button" className="btn btn-small btn-primary" disabled={d.spec.assignments.length === 0}
                      onClick={() => { onSelectDesign(d.id); onNext() }}>Preview this</button>
                    <button type="button" className="btn btn-small" disabled={busy} onClick={() => startEdit(d)}>Edit</button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </aside>
      </div>
    </section>
  )
}
