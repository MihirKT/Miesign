import { useCallback, useEffect, useState } from 'react'
import StepRail from './components/StepRail'
import { api, errorMessage } from './lib/api'
import { resumeStep, unlockedSteps, type StepKey } from './lib/steps'
import type { Material, Project, StateEntry } from './lib/types'
import DesignStep from './steps/DesignStep'
import EstimateStep from './steps/EstimateStep'
import PartsStep from './steps/PartsStep'
import PhotoStep from './steps/PhotoStep'
import PreviewStep from './steps/PreviewStep'
import ReportStep from './steps/ReportStep'

export default function App() {
  const [project, setProject] = useState<Project | null>(null)
  const [catalog, setCatalog] = useState<Material[]>([])
  const [states, setStates] = useState<StateEntry[]>([])
  const [step, setStep] = useState<StepKey>('photo')
  const [designId, setDesignId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.catalog().then(setCatalog).catch((e) => setError(errorMessage(e)))
    api.locations().then(setStates).catch((e) => setError(errorMessage(e)))
    const id = new URLSearchParams(window.location.search).get('p')
    if (id) {
      api.getProject(id)
        .then((p) => {
          setProject(p)
          setStep(resumeStep(p))
        })
        .catch((e) => setError(errorMessage(e)))
    }
  }, [])

  const ensureProject = useCallback(async () => {
    if (project) return project
    const created = await api.createProject()
    window.history.replaceState(null, '', `?p=${created.id}`)
    setProject(created)
    return created
  }, [project])

  const unlocked = unlockedSteps(project)
  const design = project?.designs.find((d) => d.id === designId) ?? project?.designs[0] ?? null
  const go = (next: StepKey) => {
    setStep(next)
    window.scrollTo({ top: 0 })
  }

  return (
    <div className="app">
      <StepRail step={step} unlocked={unlocked} onSelect={go} />
      <main key={step} className="fade-in">
        {error && (
          <p className="notice error" role="alert">
            {error} <a href="/">Start a new project</a>
          </p>
        )}
        {step === 'photo' && (
          <PhotoStep project={project} states={states} ensureProject={ensureProject} onChange={setProject} onNext={() => go('parts')} />
        )}
        {step === 'parts' && project && <PartsStep project={project} onChange={setProject} onNext={() => go('design')} />}
        {step === 'design' && project && (
          <DesignStep
            project={project}
            catalog={catalog}
            activeDesignId={design?.id ?? null}
            onChange={setProject}
            onSelectDesign={setDesignId}
            onNext={() => go('preview')}
          />
        )}
        {step === 'preview' && project && design && (
          <PreviewStep project={project} design={design} onChange={setProject} onSelectDesign={setDesignId} onNext={() => go('estimate')} />
        )}
        {step === 'estimate' && project && design && <EstimateStep project={project} design={design} onNext={() => go('report')} />}
        {step === 'report' && project && design && <ReportStep project={project} design={design} />}
        <footer className="footer">
          Advisory estimate from one photo. Confirm measurements and prices with your contractor before work begins.
        </footer>
      </main>
    </div>
  )
}
