import { dayMs, shortDate } from '../utils'
import { useLayoutEffect, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from 'react'

export interface Point {
  date: string
  value: number
}

const PAD = { top: 16, right: 16, bottom: 26, left: 44 }

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(0)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(el)
    return () => observer.disconnect()
  }, [])
  return [ref, width] as const
}


// Round tick values whose first and last ticks enclose [min, max], so they double as the domain.
function niceTicks(min: number, max: number, count = 4): number[] {
  const span = max - min || 1
  const raw = span / count
  const mag = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw
  const ticks = []
  for (let t = Math.floor(min / step) * step; t < max + step - 1e-9; t += step) {
    ticks.push(Math.round(t * 100) / 100)
  }
  return ticks
}

function useActiveIndex(count: number) {
  const [active, setActive] = useState<number | null>(null)
  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
    e.preventDefault()
    const delta = e.key === 'ArrowRight' ? 1 : -1
    setActive((i) => Math.min(count - 1, Math.max(0, (i ?? count - 1) + delta)))
  }
  const focusProps = {
    tabIndex: 0,
    onKeyDown,
    onFocus: () => setActive((i) => i ?? count - 1),
    onBlur: () => setActive(null),
  }
  return { active, setActive, focusProps }
}

function Tooltip({ x, children }: { x: number; children: ReactNode }) {
  return (
    <div className="chart-tooltip" style={{ left: x }}>
      {children}
    </div>
  )
}

export function LineChart({
  points,
  band,
  height = 220,
  format,
  label,
}: {
  points: Point[]
  band?: [number, number]
  height?: number
  format: (v: number) => string
  label: string
}) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const { active, setActive, focusProps } = useActiveIndex(points.length)

  if (points.length === 0) {
    return <div className="chart-empty">No weigh-ins in this period yet.</div>
  }

  const values = points.map((p) => p.value)
  const lo = Math.min(...values, ...(band ?? []))
  const hi = Math.max(...values, ...(band ?? []))
  const pad = Math.max((hi - lo) * 0.05, 0.5)
  const ticks = niceTicks(lo - pad, hi + pad)
  const yMin = ticks[0]
  const yMax = ticks[ticks.length - 1]

  const innerW = Math.max(width - PAD.left - PAD.right, 1)
  const innerH = height - PAD.top - PAD.bottom
  const t0 = dayMs(points[0].date)
  const t1 = dayMs(points[points.length - 1].date)
  const x = (iso: string) => PAD.left + (t1 === t0 ? innerW / 2 : ((dayMs(iso) - t0) / (t1 - t0)) * innerW)
  const y = (v: number) => PAD.top + (1 - (v - yMin) / (yMax - yMin)) * innerH

  const path = points.map((p, i) => `${i ? 'L' : 'M'}${x(p.date)},${y(p.value)}`).join(' ')
  const xLabels = t1 === t0 ? [points[0]] : [points[0], points[points.length - 1]]

  const onPointerMove = (e: PointerEvent<SVGRectElement>) => {
    const box = e.currentTarget.getBoundingClientRect()
    const px = e.clientX - box.left + PAD.left
    let best = 0
    points.forEach((p, i) => {
      if (Math.abs(x(p.date) - px) < Math.abs(x(points[best].date) - px)) best = i
    })
    setActive(best)
  }

  const current = active !== null ? points[active] : null

  return (
    <div className="chart" ref={ref}>
      {width > 0 && (
        <svg height={height} role="img" aria-label={label} {...focusProps}>
          {band && (
            <>
              <rect
                x={PAD.left}
                width={innerW}
                y={y(band[1])}
                height={Math.max(y(band[0]) - y(band[1]), 0)}
                fill="var(--chart-band)"
              />
              <text className="ref-label" x={PAD.left + 6} y={y(band[1]) + 13}>
                Healthy range
              </text>
            </>
          )}
          <g className="axis">
            {ticks.map((t) => (
              <g key={t}>
                <line className="grid-line" x1={PAD.left} x2={PAD.left + innerW} y1={y(t)} y2={y(t)} />
                <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end">
                  {t}
                </text>
              </g>
            ))}
            {xLabels.map((p, i) => (
              <text
                key={p.date}
                x={x(p.date)}
                y={height - 6}
                textAnchor={xLabels.length === 1 ? 'middle' : i === 0 ? 'start' : 'end'}
              >
                {shortDate(p.date)}
              </text>
            ))}
          </g>
          <path d={path} fill="none" stroke="var(--chart-1)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
          {current && (
            <line className="crosshair" x1={x(current.date)} x2={x(current.date)} y1={PAD.top} y2={PAD.top + innerH} />
          )}
          {points.map((p, i) => (
            <circle
              key={p.date}
              cx={x(p.date)}
              cy={y(p.value)}
              r={i === active ? 5.5 : 4}
              fill="var(--chart-1)"
              stroke="var(--surface)"
              strokeWidth={2}
            />
          ))}
          <rect
            x={PAD.left - 12}
            y={0}
            width={innerW + 24}
            height={height}
            fill="transparent"
            onPointerMove={onPointerMove}
            onPointerLeave={() => setActive(null)}
          />
        </svg>
      )}
      {current && (
        <Tooltip x={x(current.date)}>
          <strong>{format(current.value)}</strong>
          <span className="muted">{shortDate(current.date)}</span>
        </Tooltip>
      )}
    </div>
  )
}

export function ColumnChart({
  points,
  target,
  height = 220,
  format,
  label,
}: {
  points: Point[]
  target?: number
  height?: number
  format: (v: number) => string
  label: string
}) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const { active, setActive, focusProps } = useActiveIndex(points.length)

  const max = Math.max(...points.map((p) => p.value), target ?? 0, 1)
  const ticks = niceTicks(0, max * 1.05)
  const yMax = ticks[ticks.length - 1]

  const innerW = Math.max(width - PAD.left - PAD.right, 1)
  const innerH = height - PAD.top - PAD.bottom
  const band = innerW / Math.max(points.length, 1)
  const barW = Math.max(Math.min(24, band - 2), 1)
  const x = (i: number) => PAD.left + i * band + (band - barW) / 2
  const y = (v: number) => PAD.top + (1 - v / yMax) * innerH
  const base = PAD.top + innerH

  const column = (i: number, v: number) => {
    const top = y(v)
    const r = Math.min(4, barW / 2, base - top)
    const left = x(i)
    const right = left + barW
    return `M${left},${base} V${top + r} Q${left},${top} ${left + r},${top} H${right - r} Q${right},${top} ${right},${top + r} V${base} Z`
  }

  const labelEvery = Math.ceil(points.length / Math.max(Math.floor(innerW / 56), 1))
  const current = active !== null ? points[active] : null

  return (
    <div className="chart" ref={ref}>
      {width > 0 && (
        <svg height={height} role="img" aria-label={label} {...focusProps}>
          <g className="axis">
            {ticks.map((t) => (
              <g key={t}>
                <line className="grid-line" x1={PAD.left} x2={PAD.left + innerW} y1={y(t)} y2={y(t)} />
                <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end">
                  {t.toLocaleString()}
                </text>
              </g>
            ))}
            {points.map((p, i) =>
              (points.length - 1 - i) % labelEvery === 0 ? (
                <text key={p.date} x={x(i) + barW / 2} y={height - 6} textAnchor="middle">
                  {shortDate(p.date)}
                </text>
              ) : null,
            )}
          </g>
          {points.map((p, i) =>
            p.value > 0 ? (
              <path
                key={p.date}
                d={column(i, p.value)}
                fill="var(--chart-1)"
                opacity={active === null || active === i ? 1 : 0.55}
              />
            ) : null,
          )}
          {target !== undefined && (
            <g>
              <line className="ref-line" x1={PAD.left} x2={PAD.left + innerW} y1={y(target)} y2={y(target)} />
              <text className="ref-label" x={PAD.left + innerW} y={y(target) - 5} textAnchor="end">
                Target {target.toLocaleString()}
              </text>
            </g>
          )}
          {points.map((p, i) => (
            <rect
              key={p.date}
              x={PAD.left + i * band}
              y={PAD.top}
              width={band}
              height={innerH}
              fill="transparent"
              onPointerEnter={() => setActive(i)}
              onPointerLeave={() => setActive(null)}
            />
          ))}
        </svg>
      )}
      {current && (
        <Tooltip x={x(active!) + barW / 2}>
          <strong>{format(current.value)}</strong>
          <span className="muted">{shortDate(current.date)}</span>
        </Tooltip>
      )}
    </div>
  )
}

export function DataTable({ columns, rows }: { columns: string[]; rows: (string | number)[][] }) {
  return (
    <details className="table-toggle">
      <summary>Show as table</summary>
      <table className="chart-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={String(r[0])}>
              {r.map((cell, i) => (
                <td key={i}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  )
}
