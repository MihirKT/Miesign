import { useState, type CSSProperties } from 'react'

interface Props {
  before: string
  after: string
  alt: string
}

export default function CompareSlider({ before, after, alt }: Props) {
  const [pos, setPos] = useState(50)
  return (
    <figure className="stack" style={{ margin: 0 }}>
      <div className="compare" style={{ '--pos': `${pos}%` } as CSSProperties}>
        <img src={before} alt={`${alt}, original`} />
        <img className="after" src={after} alt={`${alt}, redesigned`} />
        <span className="divider" aria-hidden="true" />
      </div>
      <input
        className="compare-range"
        type="range"
        min={0}
        max={100}
        value={pos}
        aria-label="Slide to compare original and redesigned"
        onChange={(e) => setPos(Number(e.target.value))}
      />
      <figcaption className="row" style={{ justifyContent: 'space-between' }}>
        <span className="label">Original</span>
        <span className="label">Redesigned</span>
      </figcaption>
    </figure>
  )
}
