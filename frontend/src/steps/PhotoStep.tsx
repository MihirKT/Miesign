import { useState } from 'react'
import CitySelect from '../components/CitySelect'
import { api, errorMessage } from '../lib/api'
import { useElapsed } from '../lib/hooks'
import type { Project, StateEntry } from '../lib/types'

interface Props {
  project: Project | null
  states: StateEntry[]
  ensureProject: () => Promise<Project>
  onChange: (p: Project) => void
  onNext: () => void
}

export default function PhotoStep({ project, states, ensureProject, onChange, onNext }: Props) {
  const [busy, setBusy] = useState(false)
  const [over, setOver] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const elapsed = useElapsed(busy)

  async function upload(file: File) {
    setBusy(true)
    setError(null)
    try {
      const p = await ensureProject()
      onChange(await api.uploadPhoto(p.id, file))
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  async function makePrimary(photoId: string) {
    if (!project) return
    setError(null)
    try {
      onChange(await api.setPrimary(project.id, photoId))
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  async function saveLocation(state: string, city: string) {
    const p = await ensureProject()
    onChange(await api.updateProject(p.id, { state, city }))
  }

  const pick = (files: FileList | null) => {
    const file = files?.[0]
    if (file) void upload(file)
  }

  return (
    <section aria-labelledby="photo-h">
      <header className="stage-head">
        <p className="label">01 · Photo</p>
        <h1 id="photo-h">Start with one clear photo of the front.</h1>
        <p className="lede">Stand across the road in daylight so the whole front fits. We check every photo before using it.</p>
      </header>
      <div className="workspace">
        <div className="stack">
          <label
            className="dropzone"
            data-over={over}
            onDragOver={(e) => { e.preventDefault(); setOver(true) }}
            onDragLeave={() => setOver(false)}
            onDrop={(e) => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files) }}
          >
            <input
              className="sr-only"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={busy}
              onChange={(e) => { pick(e.target.files); e.target.value = '' }}
            />
            <strong>{busy ? `Checking your photo… ${elapsed}s` : 'Choose a photo or drop it here'}</strong>
            <span className="lede">JPG, PNG or WEBP · at least 800 px on the short side · up to 15 MB</span>
          </label>
          {error && <p className="notice error" role="alert">{error}</p>}
          {project && project.photos.length > 0 && (
            <ul className="thumbs" aria-label="Your photos">
              {project.photos.map((ph) => (
                <li key={ph.id} className="thumb" data-primary={ph.id === project.primaryPhotoId}>
                  <img src={ph.url} alt="Uploaded photo of the house" />
                  {ph.qualityOk ? (
                    ph.id === project.primaryPhotoId ? (
                      <span className="badge web">In use</span>
                    ) : (
                      <button type="button" className="btn btn-small" onClick={() => makePrimary(ph.id)}>Use this photo</button>
                    )
                  ) : (
                    <div className="notice error">
                      <strong>Can't use this one</strong>
                      <ul>{[...ph.issues, ...ph.tips].map((t) => <li key={t}>{t}</li>)}</ul>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
        <aside className="panel">
          <h2>Where is the house?</h2>
          <p className="lede">Material and labour rates are looked up for your city.</p>
          <CitySelect states={states} state={project?.state ?? ''} city={project?.city ?? ''} onSave={saveLocation} />
          <button type="button" className="btn btn-primary" disabled={!project?.primaryPhotoId} onClick={onNext}>
            Next: check the parts
          </button>
        </aside>
      </div>
    </section>
  )
}
