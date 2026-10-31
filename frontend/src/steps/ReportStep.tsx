/**
 * Step 06: download the PDF report and copy the project link.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

import { useState } from 'react'
import { api } from '../lib/api'
import type { Design, Project } from '../lib/types'

interface Props {
  project: Project
  design: Design
}

export default function ReportStep({ project, design }: Props) {
  const [copied, setCopied] = useState<'idle' | 'done' | 'error'>('idle')
  const link = `${window.location.origin}/?p=${project.id}`

  async function copyLink() {
    setCopied('idle')
    try {
      await navigator.clipboard.writeText(link)
      setCopied('done')
    } catch {
      setCopied('error')
    }
  }

  return (
    <section aria-labelledby="report-h">
      <header className="stage-head">
        <p className="label">06 · Report</p>
        <h1 id="report-h">Take this to your contractor.</h1>
        <p className="lede">
          The PDF has {design.renderUrl ? 'your original and redesigned photo' : 'your photo (render a preview on step 04 to include the redesign)'}, the materials for “{design.name}”, the measured areas, quantities and the full cost breakdown.
        </p>
      </header>
      <div className="stack" style={{ maxWidth: '60ch' }}>
        <div className="row">
          <a className="btn btn-primary" href={api.reportUrl(design.id)} download>Download report (PDF)</a>
          <button type="button" className="btn" onClick={copyLink}>
            {copied === 'done' ? 'Link copied' : 'Copy project link'}
          </button>
        </div>
        <p role="status" aria-live="polite" className={copied === 'done' ? 'notice ok' : undefined}>
          {copied === 'done' ? 'Link copied.' : ''}
        </p>
        {copied === 'error' && (
          <p className="notice error" role="alert">Couldn't copy. The link is: {link}</p>
        )}
        <p className="notice">Anyone with the project link can open and edit this project. Share it only with people you trust.</p>
      </div>
    </section>
  )
}
