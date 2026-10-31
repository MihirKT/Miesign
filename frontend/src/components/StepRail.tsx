import type { CSSProperties } from 'react'
import { STEPS, type StepKey } from '../lib/steps'

interface Props {
  step: StepKey
  unlocked: Set<StepKey>
  onSelect: (step: StepKey) => void
}

export default function StepRail({ step, unlocked, onSelect }: Props) {
  const index = STEPS.findIndex((s) => s.key === step)
  return (
    <>
      <nav className="rail" aria-label="Steps">
        <span className="wordmark">Facade</span>
        <ol>
          {STEPS.map((s, i) => (
            <li key={s.key}>
              <button
                type="button"
                className="step-link"
                aria-current={s.key === step ? 'step' : undefined}
                disabled={!unlocked.has(s.key)}
                onClick={() => onSelect(s.key)}
              >
                <span className="num">{String(i + 1).padStart(2, '0')}</span>
                {s.label}
              </button>
            </li>
          ))}
        </ol>
      </nav>
      <div className="mobile-bar">
        <div className="inner">
          <span>
            Step {index + 1} of {STEPS.length} · <strong>{STEPS[index].label}</strong>
          </span>
          <label className="sr-only" htmlFor="step-jump">Go to step</label>
          <select id="step-jump" className="step-jump" value={step} onChange={(e) => onSelect(e.target.value as StepKey)}>
            {STEPS.map((s) => (
              <option key={s.key} value={s.key} disabled={!unlocked.has(s.key)}>{s.label}</option>
            ))}
          </select>
        </div>
        <div className="progress" style={{ '--done': (index + 1) / STEPS.length } as CSSProperties} />
      </div>
    </>
  )
}
