import { useCallback, useEffect, useRef, useState } from 'react'
import RateCell from '../components/RateCell'
import { api, errorMessage } from '../lib/api'
import { groupByCategory } from '../lib/estimate'
import { inr, num, shortDate } from '../lib/format'
import { useCountUp } from '../lib/hooks'
import type { Design, Estimate, Project, RateRow } from '../lib/types'

interface Props {
  project: Project
  design: Design
  onNext: () => void
}

const SOURCE_LABEL: Record<RateRow['source'], string> = { web: 'Web', estimated: 'Estimate', override: 'Yours' }

function hostOf(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

export default function EstimateStep({ project, design, onNext }: Props) {
  const [estimate, setEstimate] = useState<Estimate | null>(null)
  const [rates, setRates] = useState<RateRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [rateError, setRateError] = useState<string | null>(null)
  const [rateOk, setRateOk] = useState('')
  const saving = useRef(false)
  const total = useCountUp(estimate?.grandTotal ?? 0)

  const load = useCallback(async () => {
    setError(null)
    try {
      // Estimate first: it triggers (and caches) the city rate search the rates call then reuses.
      const e = await api.estimate(design.id)
      setEstimate(e)
      setRates(await api.rates(project.state, project.city, project.id))
    } catch (err) {
      setError(errorMessage(err))
      setEstimate(null)
      setRates([])
    } finally {
      setLoading(false)
    }
  }, [design.id, project.id, project.state, project.city])

  useEffect(() => {
    setLoading(true)
    void load()
  }, [load])

  async function override(materialId: string, change: { materialRate?: number; laborRate?: number }) {
    if (saving.current) throw new Error('Another rate is still saving.')
    saving.current = true
    setRateError(null)
    setRateOk('')
    try {
      await api.overrideRate(project.id, materialId, change)
      await load()
      setRateOk('Rate updated. Totals recalculated.')
    } catch (err) {
      setRateError(errorMessage(err))
      // Resync so the displayed total never disagrees with the server.
      await load()
      throw err
    } finally {
      saving.current = false
    }
  }

  const rateFor = (id: string) => rates.find((r) => r.materialId === id)
  const sources = [...new Set(rates.flatMap((r) => r.sources))]

  return (
    <section aria-labelledby="estimate-h">
      <header className="stage-head">
        <p className="label">05 · Estimate</p>
        <h1 id="estimate-h">What it will cost, line by line.</h1>
        <p className="lede">
          {project.city
            ? `Rates for ${project.city}, ${project.state}. Change any rate your contractor quoted and the totals update.`
            : 'No city set, so average rates are used. Add your city on step 01 for local prices.'}
        </p>
      </header>
      {loading && <p className="progress-line" role="status">Measuring surfaces and looking up local rates…</p>}
      {error && <p className="notice error" role="alert">{error} <button type="button" className="btn btn-small" onClick={() => { setLoading(true); setRateError(null); setRateOk(''); void load() }}>Try again</button></p>}
      <p role="status" aria-live="polite" className={rateOk ? 'notice ok' : undefined}>{rateOk}</p>
      {rateError && <p className="notice error" role="alert">{rateError}</p>}
      {estimate && (
        <div className="stack">
          {estimate.warnings.length > 0 && <div className="notice warn"><ul>{estimate.warnings.map((w) => <li key={w}>{w}</li>)}</ul></div>}
          {estimate.lines.length === 0 ? (
            <p className="notice">This design has no priced materials. Pick materials on step 03.</p>
          ) : (
            <div className="table-scroll">
              <table className="cost-table">
                <thead>
                  <tr>
                    <th scope="col">Item</th>
                    <th scope="col" className="num">Area / length</th>
                    <th scope="col" className="num">Quantity</th>
                    <th scope="col" className="num">Material ₹</th>
                    <th scope="col" className="num">Labour ₹</th>
                    <th scope="col" className="num">Material</th>
                    <th scope="col" className="num">Labour</th>
                    <th scope="col" className="num">Total</th>
                  </tr>
                </thead>
                {groupByCategory(estimate.lines).map((g) => (
                  <tbody key={g.category}>
                    {g.lines.map((line) => {
                      const rate = rateFor(line.materialId)
                      return (
                        <tr key={line.materialId}>
                          <td>
                            <strong>{line.name}</strong>
                            <div className="row">
                              <span className="badge">{line.targets.join(' · ')}</span>
                              <span className={`badge ${line.rateSource}`}>
                                {SOURCE_LABEL[line.rateSource]}{rate?.fetchedAt ? ` · ${shortDate(rate.fetchedAt)}` : ''}
                              </span>
                            </div>
                          </td>
                          <td className="num">{num(line.measure)} {line.rateUnit}</td>
                          <td className="num">{num(line.quantity)} {line.qtyUnit}</td>
                          <td className="num">
                            <RateCell value={line.materialRate} label={`${line.name} material rate per ${line.rateUnit}`}
                              onCommit={(v) => override(line.materialId, { materialRate: v })} />
                          </td>
                          <td className="num">
                            <RateCell value={line.laborRate} label={`${line.name} labour rate per ${line.rateUnit}`}
                              onCommit={(v) => override(line.materialId, { laborRate: v })} />
                          </td>
                          <td className="num">{inr(line.materialCost)}</td>
                          <td className="num">{inr(line.laborCost)}</td>
                          <td className="num">{inr(line.total)}</td>
                        </tr>
                      )
                    })}
                    <tr className="subtotal">
                      <td colSpan={5}>{g.category} subtotal</td>
                      <td className="num">{inr(g.materialCost)}</td>
                      <td className="num">{inr(g.laborCost)}</td>
                      <td className="num">{inr(g.total)}</td>
                    </tr>
                  </tbody>
                ))}
              </table>
            </div>
          )}
          <details>
            <summary>How this was calculated</summary>
            <ul>{estimate.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
            {sources.length > 0 && (
              <>
                <p className="label">Rate sources</p>
                <ul>{sources.map((s) => <li key={s}><a href={s} target="_blank" rel="noreferrer noopener">{hostOf(s)}</a></li>)}</ul>
              </>
            )}
          </details>
          <div className="total-bar">
            <span>Estimated total</span>
            <span className="amount" aria-live="polite">{inr(total)}</span>
          </div>
          <button type="button" className="btn btn-primary" onClick={onNext}>Next: get the report</button>
        </div>
      )}
    </section>
  )
}
