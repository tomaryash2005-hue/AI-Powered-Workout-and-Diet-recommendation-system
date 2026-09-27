import type { Metrics, Progress } from '../api'
import { bmiCategory, fmt } from '../utils'
import { AlertIcon } from './Icons'

export function Ring({ progress }: { progress: Progress }) {
  const r = 52
  const c = 2 * Math.PI * r
  const ratio = progress.target > 0 ? progress.consumed / progress.target : 0
  const over = progress.remaining < 0
  return (
    <div className="ring">
      <svg viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={r} fill="none" stroke="var(--surface-2)" strokeWidth="12" />
        <circle
          cx="60"
          cy="60"
          r={r}
          fill="none"
          stroke={over ? 'var(--danger)' : 'var(--accent)'}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - Math.min(ratio, 1))}
          style={{ transition: 'stroke-dashoffset 0.4s ease' }}
        />
      </svg>
      <div className="ring-label">
        <strong>{fmt(Math.abs(progress.remaining))}</strong>
        <span>{over ? 'kcal over' : 'kcal left'}</span>
      </div>
    </div>
  )
}

export function MacroBar({
  label,
  progress,
  color,
}: {
  label: string
  progress: Progress
  color: string
}) {
  const pct = progress.target > 0 ? (progress.consumed / progress.target) * 100 : 0
  return (
    <div className="macro">
      <div className="spread">
        <span>{label}</span>
        <span className="num muted">
          <strong style={{ color: 'var(--text)' }}>{fmt(progress.consumed)}</strong> / {fmt(progress.target)} g
        </span>
      </div>
      <div
        className="bar"
        role="progressbar"
        aria-label={label}
        aria-valuenow={Math.round(progress.consumed)}
        aria-valuemax={progress.target}
      >
        <div style={{ width: `${Math.min(pct, 100)}%`, background: color }} />
      </div>
    </div>
  )
}

const BMI_MIN = 15
const BMI_MAX = 40

export function BmiScale({ bmi }: { bmi: number }) {
  const pos = ((Math.min(Math.max(bmi, BMI_MIN), BMI_MAX) - BMI_MIN) / (BMI_MAX - BMI_MIN)) * 100
  return (
    <div className="bmi-scale" aria-hidden="true">
      <div className="bmi-track">
        <div />
        <div />
        <div />
        <div />
      </div>
      <div className="bmi-marker" style={{ left: `${pos}%` }} />
      <div className="bmi-ticks">
        <span />
        <span>18.5</span>
        <span>25</span>
        <span>30</span>
      </div>
    </div>
  )
}

const CATEGORY_TAG: Record<ReturnType<typeof bmiCategory>, string> = {
  underweight: 'tag-warn',
  normal: 'tag-accent',
  overweight: 'tag-warn',
  obese: 'tag-danger',
}

export function BmiTag({ bmi }: { bmi: number }) {
  const cat = bmiCategory(bmi)
  return <span className={`tag ${CATEGORY_TAG[cat]}`}>{cat[0].toUpperCase() + cat.slice(1)}</span>
}

export function Warnings({ metrics }: { metrics: Metrics }) {
  if (!metrics.warnings.length) return null
  return (
    <div className="stack" style={{ gap: 8 }}>
      {metrics.warnings.map((w) => (
        <div className="alert alert-warn" key={w}>
          <AlertIcon />
          <span>{w}</span>
        </div>
      ))}
    </div>
  )
}
