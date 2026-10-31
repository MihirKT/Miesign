/**
 * Step 04: render the design on the photo and compare it with the original, within the per-project render cap.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

import { useState } from 'react'
import AssignmentList from '../components/AssignmentList'
import CompareSlider from '../components/CompareSlider'
import { api, errorMessage } from '../lib/api'
import { useElapsed } from '../lib/hooks'
import type { Design, Material, Project } from '../lib/types'

interface Props {
  project: Project
  design: Design
  catalog: Material[]
  onChange: (p: Project) => void
  onSelectDesign: (id: string) => void
  onNext: () => void
}

export default function PreviewStep({ project, design, catalog, onChange, onSelectDesign, onNext }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState('')
  const elapsed = useElapsed(busy)
  const photo = project.photos.find((p) => p.id === project.primaryPhotoId)
  const left = project.renderCap - project.renderCount

  async function render() {
    if (busy) return
    setBusy(true)
    setError(null)
    setDone('')
    try {
      await api.render(design.id)
      // Refetch the project: the server owns render_count, and a failed render is refunded there.
      onChange(await api.getProject(project.id))
      setDone('Preview ready.')
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  function selectDesign(id: string) {
    setError(null)
    setDone('')
    onSelectDesign(id)
  }

  return (
    <section aria-labelledby="preview-h">
      <header className="stage-head">
        <p className="label">04 · Preview</p>
        <h1 id="preview-h">See your house with the new materials.</h1>
        <p className="lede">The structure stays the same; only surfaces and colours change. Treat it as a guide, not a photograph.</p>
      </header>
      <div className="workspace">
        <div className="stack">
          {photo && design.renderUrl ? (
            <CompareSlider before={photo.url} after={design.renderUrl} alt="Your house" />
          ) : (
            photo && <img src={photo.url} alt="Your house, original" />
          )}
          {design.spec.assignments.length > 0 && (
            <div className="stack">
              <h2>What changes</h2>
              <AssignmentList assignments={design.spec.assignments} catalog={catalog} partFirst />
            </div>
          )}
          {busy && <p className="progress-line">Applying materials to your photo… {elapsed}s (usually 20–40 s)</p>}
          <p role="status" aria-live="polite" className={done ? 'notice ok' : undefined}>{done}</p>
          {error && <p className="notice error" role="alert">{error}</p>}
        </div>
        <aside className="panel">
          <div className="field">
            <label htmlFor="design-pick">Design</label>
            <select id="design-pick" value={design.id} disabled={busy} onChange={(e) => selectDesign(e.target.value)}>
              {project.designs.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>
          <button type="button" className="btn btn-primary" disabled={busy || left <= 0} aria-busy={busy} onClick={render}>
            {design.renderUrl ? 'Render again' : 'Render this design'}
          </button>
          <p className="badge">{project.renderCount} of {project.renderCap} previews used</p>
          {left <= 0 && <p className="notice warn">All previews for this project are used. You can still get the estimate and report.</p>}
          <button type="button" className="btn" onClick={onNext}>Next: see the cost</button>
        </aside>
      </div>
    </section>
  )
}
