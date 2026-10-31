import { useEffect, useState } from 'react'

interface Props {
  value: number
  label: string
  onCommit: (value: number) => Promise<void>
}

export default function RateCell({ value, label, onCommit }: Props) {
  const [draft, setDraft] = useState(String(value))
  const [state, setState] = useState<'idle' | 'saving' | 'error'>('idle')

  useEffect(() => setDraft(String(value)), [value])

  async function commit() {
    const next = Number(draft)
    if (!Number.isFinite(next) || next <= 0) {
      setState('error')
      return
    }
    if (next === value) return
    setState('saving')
    try {
      await onCommit(next)
      setState('idle')
    } catch {
      setState('error')
    }
  }

  return (
    <input
      className="rate-input"
      type="number"
      inputMode="decimal"
      min={1}
      step="any"
      aria-label={label}
      aria-invalid={state === 'error'}
      aria-busy={state === 'saving'}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === 'Enter') e.currentTarget.blur()
        if (e.key === 'Escape') {
          setDraft(String(value))
          setState('idle')
        }
      }}
    />
  )
}
