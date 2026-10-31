import { useMemo, useState } from 'react'
import { api, errorMessage } from '../lib/api'
import { typeLabel } from '../lib/format'
import { useElapsed } from '../lib/hooks'
import type { Answers, ComponentType, Design, DesignSpec, Material, Project } from '../lib/types'

type Tab = 'describe' | 'guided' | 'manual'
type Pick = { materialId: string; color: string | null }

const EXAMPLES = [
  'Light grey texture paint on the walls, slate cladding on the pillars, glass railing on the balcony',
  'Keep it simple: cream paint everywhere and black steel railings',
]
const CHOICES = {
  budget: [['low', 'Tight'], ['mid', 'Balanced'], ['high', 'Premium']],
  climate: [['moderate', 'Moderate'], ['heavy_rain', 'Heavy rain'], ['coastal', 'Coastal'], ['hot_dry', 'Hot and dry']],
  style: [['modern', 'Modern'], ['traditional', 'Traditional'], ['minimal', 'Minimal'], ['luxe', 'Luxe']],
  maintenance: [['low', 'Low upkeep'], ['medium', 'Some upkeep is fine']],
} as const
const MODE_LABEL: Record<Design['mode'], string> = { free_text: 'From your words', guided: 'Suggested', manual: 'Picked by you' }
// Neutral starting swatch for the colour picker; stored only when the user changes it.
const DEFAULT_SWATCH = '#d9d4cc'

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
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState<string | null>(null)
  const elapsed = useElapsed(busy)

  const byId = useMemo(() => new Map(catalog.map((m) => [m.id, m])), [catalog])
  const present = useMemo(
    () => [...new Set(project.components.map((c) => c.type))].filter((t) => t !== 'window' && t !== 'door'),
    [project.components],
  )

  async function create(action: () => Promise<Design[]>, success: string) {
    if (busy) return
    setBusy(true)
    setError(null)
    setDone(null)
    try {
      const created = await action()
      const ids = new Set(created.map((d) => d.id))
      onChange({ ...project, designs: [...created, ...project.designs.filter((d) => !ids.has(d.id))] })
      onSelectDesign(created[0].id)
      setDone(success)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  function manualSpec(): DesignSpec {
    const assignments = Object.entries(picks)
      .filter(([, p]) => p?.materialId)
      .map(([type, p]) => ({ target: `type:${type}`, materialId: p?.materialId ?? '', color: p?.color ?? null, finish: '' }))
    return { style: '', palette: [], assignments, keepUnchanged: [] }
  }

  function startEdit(d: Design) {
    const next: Partial<Record<ComponentType, Pick>> = {}
    for (const a of d.spec.assignments) {
      if (a.target.startsWith('type:')) next[a.target.slice(5) as ComponentType] = { materialId: a.materialId, color: a.color }
    }
    setPicks(next)
    setEditing(d)
    setTab('manual')
  }

  const summary = (d: Design) =>
    d.spec.assignments.map((a) => `${byId.get(a.materialId)?.name ?? a.materialId} on ${typeLabel(a.target.split(':')[1] ?? '')}`).join(' · ')

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
              <button key={t} type="button" role="tab" className="tab" aria-selected={tab === t} onClick={() => setTab(t)}>
                {t === 'describe' ? 'Describe it' : t === 'guided' ? 'Help me choose' : 'Pick materials'}
              </button>
            ))}
          </div>

          {tab === 'describe' && (
            <fieldset className="stack" role="tabpanel" disabled={busy} style={{ border: 0, padding: 0, margin: 0, minWidth: 0 }}>
              <div className="field">
                <label htmlFor="design-text">What should the house look like?</label>
                <textarea id="design-text" maxLength={1000} value={text} onChange={(e) => setText(e.target.value)} />
              </div>
              <div className="chips" aria-label="Examples">
                {EXAMPLES.map((ex) => <button key={ex} type="button" className="chip" onClick={() => setText(ex)}>{ex.split(',')[0]}</button>)}
              </div>
              <button type="button" className="btn btn-primary" disabled={busy || text.trim().length < 3} aria-busy={busy}
                onClick={() => create(() => api.designFromText(project.id, text), 'Design created.')}>
                {busy ? `Reading your request… ${elapsed}s` : 'Create design'}
              </button>
            </fieldset>
          )}

          {tab === 'guided' && (
            <fieldset className="stack" role="tabpanel" disabled={busy} style={{ border: 0, padding: 0, margin: 0, minWidth: 0 }}>
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
              <div className="field" role="group" aria-labelledby="q-keep">
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
              </div>
              <button type="button" className="btn btn-primary" disabled={busy} aria-busy={busy}
                onClick={() => create(() => api.recommend(project.id, answers), '3 designs suggested.')}>
                {busy ? `Putting options together… ${elapsed}s` : 'Suggest 3 designs'}
              </button>
            </fieldset>
          )}

          {tab === 'manual' && (
            <fieldset className="stack" role="tabpanel" disabled={busy} style={{ border: 0, padding: 0, margin: 0, minWidth: 0 }}>
              {editing && <p className="notice">Editing “{editing.name}”. Saving updates it.</p>}
              {present.map((t) => {
                const options = catalog.filter((m) => m.appliesTo.includes(t))
                const pick = picks[t]
                const chosen = pick ? byId.get(pick.materialId) : undefined
                return (
                  <div key={t} className="field">
                    <label htmlFor={`m-${t}`}>{typeLabel(t)}</label>
                    <div className="row">
                      <select id={`m-${t}`} value={pick?.materialId ?? ''} style={{ flex: '1 1 200px' }}
                        onChange={(e) => setPicks((p) => ({ ...p, [t]: { materialId: e.target.value, color: p[t]?.color ?? null } }))}>
                        <option value="">Leave as it is</option>
                        {options.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                      </select>
                      <input type="color" aria-label={`${typeLabel(t)} colour`} disabled={!pick?.materialId}
                        value={pick?.color ?? DEFAULT_SWATCH}
                        onChange={(e) => setPicks((p) => ({ ...p, [t]: { materialId: p[t]?.materialId ?? '', color: e.target.value } }))} />
                    </div>
                    {chosen && <span className="badge">Lasts {chosen.durabilityYears} yrs · {chosen.maintenance} upkeep</span>}
                  </div>
                )
              })}
              <button type="button" className="btn btn-primary" disabled={busy || manualSpec().assignments.length === 0} aria-busy={busy}
                onClick={() => create(async () => [await api.saveDesign(project.id, { id: editing?.id, name: editing?.name ?? 'My design', spec: manualSpec() })], 'Design saved.')}>
                {editing ? 'Update design' : 'Save design'}
              </button>
            </fieldset>
          )}
          {done && <p className="notice ok" role="status">{done}</p>}
          {error && <p className="notice error" role="alert">{error}</p>}
        </div>

        <aside className="panel">
          <h2>Your designs</h2>
          {project.designs.length === 0 ? (
            <p className="notice">No designs yet. Create one on the left.</p>
          ) : (
            <div className="design-list">
              {project.designs.map((d) => (
                <article key={d.id} className="design" data-active={d.id === activeDesignId}>
                  <span className="badge">{MODE_LABEL[d.mode]}</span>
                  <h3>{d.name}</h3>
                  <p className="lede">{summary(d) || 'No materials applied.'}</p>
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
