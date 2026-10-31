import { useEffect, useState } from 'react'
import { errorMessage } from '../lib/api'
import type { StateEntry } from '../lib/types'

const OTHER = '__other'

interface Props {
  states: StateEntry[]
  state: string
  city: string
  onSave: (state: string, city: string) => Promise<void>
}

export default function CitySelect({ states, state, city, onSave }: Props) {
  const [s, setS] = useState(state)
  const [c, setC] = useState(city)
  const [otherChosen, setOtherChosen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)

  useEffect(() => {
    setS(state)
    setC(city)
  }, [state, city])

  const cities = states.find((x) => x.name === s)?.cities ?? []
  const other = otherChosen || (c !== '' && !cities.some((x) => x.name === c))

  async function save() {
    setBusy(true)
    setMsg(null)
    try {
      await onSave(s, c.trim())
      setMsg({ kind: 'ok', text: `Rates will use ${c.trim()}, ${s}.` })
    } catch (e) {
      setMsg({ kind: 'error', text: errorMessage(e) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="stack">
      <div className="field">
        <label htmlFor="state">State</label>
        <select id="state" value={s} onChange={(e) => { setS(e.target.value); setC(''); setOtherChosen(false) }}>
          <option value="">Choose a state</option>
          {states.map((x) => <option key={x.name} value={x.name}>{x.name}</option>)}
        </select>
      </div>
      <div className="field">
        <label htmlFor="city">City</label>
        <select
          id="city"
          value={other ? OTHER : c}
          disabled={!s}
          onChange={(e) => {
            const v = e.target.value
            setOtherChosen(v === OTHER)
            setC(v === OTHER ? '' : v)
          }}
        >
          <option value="">Choose a city</option>
          {cities.map((x) => <option key={x.name} value={x.name}>{x.name}</option>)}
          <option value={OTHER}>Other city</option>
        </select>
      </div>
      {other && (
        <div className="field">
          <label htmlFor="city-other">City name</label>
          <input id="city-other" type="text" maxLength={80} value={c} onChange={(e) => setC(e.target.value)} />
        </div>
      )}
      <button type="button" className="btn" disabled={!s || !c.trim() || busy} aria-busy={busy} onClick={save}>
        {busy ? 'Saving…' : 'Save location'}
      </button>
      {msg && <p className={`notice ${msg.kind}`} role="status">{msg.text}</p>}
    </div>
  )
}
