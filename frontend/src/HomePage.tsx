/**
 * Home page shown before a project starts: what Miesign does, a real before/after, and the way in.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

import CompareSlider from './components/CompareSlider'
import { PAINT_PRESETS, SHADE_FAMILIES } from './lib/palette'
import { STEPS } from './lib/steps'

const STEP_NOTES: Record<string, string> = {
  photo: 'One daytime photo of the front. Phone and WhatsApp photos work.',
  parts: 'Walls, windows, balconies, pillars, parapets, gates and railings are found for you. Drag to fix any.',
  design: 'Describe it, answer a few questions, or pick materials and shades part by part.',
  preview: 'Your own house, redesigned, with a slider to compare it with the original.',
  estimate: 'Area, quantity with wastage, material and labour cost at your city’s rates. Change any rate.',
  report: 'A PDF to take to your contractor.',
}

const FACTS = [
  { value: `${PAINT_PRESETS.length}`, label: 'named paint shades, plus any colour you pick' },
  { value: '12', label: 'materials: paint, texture, stone, tiles, panels and railings' },
  { value: '14', label: 'styles, from Kerala tropical to Art Deco' },
  { value: '91', label: 'Indian cities with local material and labour rates' },
]

export default function HomePage({ onStart }: { onStart: () => void }) {
  return (
    <div className="home">
      <header className="home-bar">
        <span className="wordmark">Miesign</span>
        <button type="button" className="btn btn-primary btn-small" onClick={onStart}>Start a project</button>
      </header>

      <section className="home-hero" aria-labelledby="home-h">
        <div className="stack">
          <p className="label">Exterior renovation planner · India</p>
          <h1 id="home-h">See your house renovated before anyone picks up a brush.</h1>
          <p className="lede">
            Upload one photo of the front. Choose colours and materials for each part, see your own house redesigned,
            and get a material and cost estimate in rupees that you can take to a contractor.
          </p>
          <div className="row">
            <button type="button" className="btn btn-primary" onClick={onStart}>Start with a photo</button>
            <a className="btn" href="#how">How it works</a>
          </div>
          <p className="badge wrap">Free · no sign-up · your project is saved to its own link</p>
        </div>
        <CompareSlider before="/samples/house1-before.jpg" after="/samples/house1-after.jpg" alt="A house in Ludhiana" />
      </section>

      <div className="shade-strip" aria-hidden="true">
        {SHADE_FAMILIES.flatMap((f) => f.shades).map((s) => <span key={s.hex} style={{ background: s.hex }} />)}
      </div>

      <section className="home-facts" aria-label="What is included">
        {FACTS.map((f) => (
          <div key={f.label} className="fact">
            <span className="fact-value">{f.value}</span>
            <span>{f.label}</span>
          </div>
        ))}
      </section>

      <section id="how" className="home-section" aria-labelledby="how-h">
        <p className="label">How it works</p>
        <h2 id="how-h">Six steps, about five minutes.</h2>
        <ol className="home-steps">
          {STEPS.map((s, i) => (
            <li key={s.key}>
              <span className="num">{String(i + 1).padStart(2, '0')}</span>
              <h3>{s.label}</h3>
              <p>{STEP_NOTES[s.key]}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="home-section home-split" aria-labelledby="real-h">
        <div className="stack">
          <p className="label">Real photo, real result</p>
          <h2 id="real-h">Charcoal and white on a house in Lucknow.</h2>
          <p className="lede">
            The structure stays as it is; only surfaces and colours change. Every number in the estimate comes from
            measured areas and published rates, never from the AI guessing a total.
          </p>
          <button type="button" className="btn btn-primary" onClick={onStart}>Try it on your house</button>
        </div>
        <CompareSlider before="/samples/house3-before.jpg" after="/samples/house3-after.jpg" alt="A house in Lucknow" />
      </section>

      <footer className="footer">
        <p>Advisory estimate from one photo. Confirm measurements and prices with your contractor before work begins.</p>
        <p>Miesign · designed and built by Mihir Kapildev Tiwari</p>
      </footer>
    </div>
  )
}
