import { useEffect, useState } from 'react'
import RegionCanvas from '../components/RegionCanvas'
import { api, errorMessage } from '../lib/api'
import { num, typeLabel } from '../lib/format'
import { useElapsed } from '../lib/hooks'
import { newPartQuad } from '../lib/quad'
import { COMPONENT_TYPES, type ComponentType, type Part, type Project } from '../lib/types'

interface Props {
  project: Project
  onChange: (p: Project) => void
  onNext: () => void
}

type Busy = 'detect' | 'save' | 'scale' | null

export default function PartsStep({ project, onChange, onNext }: Props) {
  const photo = project.photos.find((p) => p.id === project.primaryPhotoId)
  const [parts, setParts] = useState<Part[]>(project.components)
  const [selected, setSelected] = useState<number | null>(null)
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState<Busy>(null)
  const [error, setError] = useState<string | null>(null)
  const [scalePart, setScalePart] = useState('')
  const [scaleFt, setScaleFt] = useState('')
  const elapsed = useElapsed(busy === 'detect')

  useEffect(() => {
    setParts(project.components)
    setDirty(false)
    setSelected(null)
  }, [project.components])

  if (!photo) {
    return <p className="notice error" role="alert">Choose a usable photo on step 01 first.</p>
  }

  async function run(kind: Exclude<Busy, null>, action: () => Promise<Project>) {
    setBusy(kind)
    setError(null)
    try {
      onChange(await action())
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(null)
    }
  }

  const edit = (i: number, patch: Partial<Part>) => {
    setParts((ps) => ps.map((p, j) => (j === i ? { ...p, ...patch, source: 'user' } : p)))
    setDirty(true)
  }
  const add = () => {
    setParts((ps) => [...ps, { type: 'wall', quad: newPartQuad(photo.width, photo.height), floor: 0, source: 'user' }])
    setSelected(parts.length)
    setDirty(true)
  }
  const remove = (i: number) => {
    setParts((ps) => ps.filter((_, j) => j !== i))
    setSelected(null)
    setDirty(true)
  }
  const savedParts = project.components.filter((p) => p.id)
  const ft = Number(scaleFt)

  return (
    <section aria-labelledby="parts-h">
      <header className="stage-head">
        <p className="label">02 · Parts</p>
        <h1 id="parts-h">Check what we found on your house.</h1>
        <p className="lede">Each coloured outline is a part we will price. Tap one to drag it or its corners; fix the type in the list.</p>
      </header>
      <div className="workspace">
        <div className="stack">
          <RegionCanvas
            src={photo.url}
            width={photo.width}
            height={photo.height}
            parts={parts}
            selected={selected}
            onSelect={setSelected}
            onChange={(i, quad) => edit(i, { quad })}
          />
          {busy === 'detect' && <p className="progress-line" role="status">Finding walls, windows and pillars… {elapsed}s</p>}
          {error && <p className="notice error" role="alert">{error}</p>}
        </div>
        <aside className="panel">
          <div className="row">
            <button type="button" className="btn btn-primary" disabled={busy !== null} aria-busy={busy === 'detect'}
              onClick={() => run('detect', () => api.detect(project.id))}>
              {parts.length ? 'Find parts again' : 'Find parts'}
            </button>
            <button type="button" className="btn" onClick={add}>Add a part</button>
          </div>
          {parts.length === 0 ? (
            <p className="notice">No parts yet. Find them automatically, or add one and drag its corners.</p>
          ) : (
            <ul className="part-list" aria-label="Parts">
              {parts.map((p, i) => (
                <li key={p.id ?? `new-${i}`} className="part-row" aria-selected={i === selected}>
                  <span className="swatch" style={{ background: `var(--region-${p.type})` }} aria-hidden="true" />
                  <select aria-label={`Part ${i + 1} type`} value={p.type} onChange={(e) => edit(i, { type: e.target.value as ComponentType })}>
                    {COMPONENT_TYPES.map((t) => <option key={t} value={t}>{typeLabel(t)}</option>)}
                  </select>
                  <div className="row">
                    <button type="button" className="btn btn-small" aria-pressed={i === selected} onClick={() => setSelected(i)}>Edit</button>
                    <button type="button" className="btn btn-small" aria-label={`Delete part ${i + 1}`} onClick={() => remove(i)}>Delete</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <button type="button" className="btn" disabled={!dirty || busy !== null} aria-busy={busy === 'save'}
            onClick={() => run('save', () => api.saveParts(project.id, parts))}>
            {busy === 'save' ? 'Saving…' : 'Save parts'}
          </button>

          <h2>Real size</h2>
          <p className="lede">
            {project.scaleSource === 'user'
              ? `Using your measurement (${num(project.pxPerFt ?? 0)} px per ft).`
              : 'Using a standard 7 ft door or 4 ft window. Enter one real height for a better estimate.'}
          </p>
          <div className="field">
            <label htmlFor="scale-part">Part you measured</label>
            <select id="scale-part" value={scalePart} onChange={(e) => setScalePart(e.target.value)}>
              <option value="">Choose a part</option>
              {savedParts.map((p, i) => <option key={p.id} value={p.id}>{typeLabel(p.type)} {i + 1}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="scale-ft">Its height in feet</label>
            <input id="scale-ft" type="number" inputMode="decimal" min={1} max={100} step="0.5" value={scaleFt}
              aria-invalid={scaleFt !== '' && !(ft >= 1 && ft <= 100)} onChange={(e) => setScaleFt(e.target.value)} />
          </div>
          <div className="row">
            <button type="button" className="btn" disabled={!scalePart || !(ft >= 1 && ft <= 100) || busy !== null}
              onClick={() => run('scale', () => api.setScale(project.id, { componentId: scalePart, realHeightFt: ft }))}>
              Use this size
            </button>
            <button type="button" className="btn btn-small" disabled={busy !== null}
              onClick={() => run('scale', () => api.setScale(project.id, { useDefault: true }))}>
              Use standard sizes
            </button>
          </div>

          {dirty && <p className="notice warn">Save your changes before moving on.</p>}
          <button type="button" className="btn btn-primary" disabled={dirty || parts.length === 0} onClick={onNext}>
            Next: choose a design
          </button>
        </aside>
      </div>
    </section>
  )
}
