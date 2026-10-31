import { useEffect, useMemo, useRef, useState } from 'react'
import { Circle, Image as KImage, Layer, Line, Stage } from 'react-konva'
import { moveCorner, translateQuad } from '../lib/quad'
import { COMPONENT_TYPES, type Part, type Quad } from '../lib/types'

const HANDLE_RADIUS = 9
const HIT_WIDTH = 24
const HANDLE_HIT_RADIUS = 22

interface Props {
  src: string
  width: number
  height: number
  parts: Part[]
  selected: number | null
  onSelect: (index: number | null) => void
  onChange: (index: number, quad: Quad) => void
}

// Konva draws on <canvas>, so read the region tokens once from CSS.
function useTokenColors() {
  return useMemo(() => {
    const css = getComputedStyle(document.documentElement)
    const read = (name: string) => css.getPropertyValue(name).trim()
    return {
      regions: Object.fromEntries(COMPONENT_TYPES.map((t) => [t, read(`--region-${t}`)])) as Record<string, string>,
      paper: read('--color-paper'),
      ink: read('--color-ink'),
    }
  }, [])
}

export default function RegionCanvas({ src, width, height, parts, selected, onSelect, onChange }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [boxWidth, setBoxWidth] = useState(0)
  const [image, setImage] = useState<HTMLImageElement | null>(null)
  const [failed, setFailed] = useState(false)
  const colors = useTokenColors()

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => setBoxWidth(entry.contentRect.width))
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    setImage(null)
    setFailed(false)
    const img = new window.Image()
    img.onload = () => setImage(img)
    img.onerror = () => setFailed(true)
    img.src = src
    return () => { img.onload = null; img.onerror = null }
  }, [src])

  const scale = boxWidth > 0 ? boxWidth / width : 0
  const active = selected !== null ? parts[selected] : undefined

  return (
    <div ref={wrapRef} className="canvas-wrap" role="img"
      aria-label="Photo with outlined parts. Use the list to edit parts with a keyboard.">
      {failed && <p className="notice error">Couldn't load the photo.</p>}
      {scale > 0 && (
        <Stage
          width={boxWidth}
          height={height * scale}
          onMouseDown={(e) => { if (e.target.getClassName() === 'Image') onSelect(null) }}
          onTouchStart={(e) => { if (e.target.getClassName() === 'Image') onSelect(null) }}
        >
          <Layer>
            {image && <KImage image={image} width={width * scale} height={height * scale} />}
            {parts.map((p, i) => (
              <Line
                key={p.id ?? `new-${i}`}
                points={p.quad.flatMap(([x, y]) => [x * scale, y * scale])}
                closed
                fill="transparent"
                stroke={colors.regions[p.type] || colors.ink}
                strokeWidth={i === selected ? 3 : 2}
                hitStrokeWidth={HIT_WIDTH}
                draggable={i === selected}
                onClick={() => onSelect(i)}
                onTap={() => onSelect(i)}
                onDragEnd={(e) => {
                  const node = e.target
                  const dx = node.x() / scale
                  const dy = node.y() / scale
                  node.position({ x: 0, y: 0 })
                  onChange(i, translateQuad(p.quad, dx, dy, width, height))
                }}
              />
            ))}
            {selected !== null && active && active.quad.map(([x, y], k) => (
              <Circle
                key={k}
                x={x * scale}
                y={y * scale}
                radius={HANDLE_RADIUS}
                fill={colors.paper}
                stroke={colors.ink}
                strokeWidth={2}
                draggable
                hitFunc={(ctx, shape) => {
                  ctx.beginPath()
                  ctx.arc(0, 0, HANDLE_HIT_RADIUS, 0, Math.PI * 2)
                  ctx.closePath()
                  ctx.fillStrokeShape(shape)
                }}
                onDragMove={(e) => {
                  const quad = moveCorner(active.quad, k, [e.target.x() / scale, e.target.y() / scale], width, height)
                  e.target.position({ x: quad[k][0] * scale, y: quad[k][1] * scale })
                  onChange(selected, quad)
                }}
              />
            ))}
          </Layer>
        </Stage>
      )}
    </div>
  )
}
