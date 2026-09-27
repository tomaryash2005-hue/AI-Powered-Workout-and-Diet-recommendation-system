import { useCallback, useState, type FormEvent } from 'react'
import { api, type Goal } from '../api'
import { ColumnChart, DataTable, LineChart } from '../components/Charts'
import { TrashIcon } from '../components/Icons'
import { fmt, shortDate, today, useAsync } from '../utils'

const RANGES = [
  { days: 7, label: '7 days' },
  { days: 30, label: '30 days' },
  { days: 90, label: '90 days' },
]

function deltaClass(delta: number, goal: Goal): string {
  if (Math.abs(delta) < 0.1) return ''
  if (goal === 'maintain') return Math.abs(delta) <= 1 ? 'delta-good' : 'delta-bad'
  return (goal === 'lose') === delta < 0 ? 'delta-good' : 'delta-bad'
}

function LogWeight({ onSaved, initial }: { onSaved: () => void; initial: number }) {
  const [date, setDate] = useState(today())
  const [weight, setWeight] = useState(String(initial))
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await api.logWeight(date, Number(weight))
      onSaved()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="stack" style={{ gap: 10 }} onSubmit={submit}>
      <div className="row" style={{ alignItems: 'flex-end' }}>
        <label className="field" style={{ flex: '1 1 140px' }}>
          <span>Date</span>
          <input className="input" type="date" value={date} max={today()} onChange={(e) => setDate(e.target.value)} required />
        </label>
        <label className="field" style={{ flex: '1 1 110px' }}>
          <span>Weight (kg)</span>
          <input
            className="input"
            type="number"
            inputMode="decimal"
            min={30}
            max={300}
            step="0.1"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            required
          />
        </label>
        <button className="btn btn-primary" disabled={busy}>
          Log weight
        </button>
      </div>
      {error && <div className="alert alert-danger">{error}</div>}
    </form>
  )
}

export default function ProgressPage() {
  const [days, setDays] = useState(30)
  const end = today()
  const { data, loading, error, reload } = useAsync(
    useCallback(
      () => Promise.all([api.getProfile(), api.weights(end, days), api.history(end, days)]),
      [end, days],
    ),
    { keepPrevious: true },
  )
  const [actionError, setActionError] = useState<string | null>(null)

  const remove = async (id: number) => {
    setActionError(null)
    try {
      await api.deleteWeight(id)
      reload()
    } catch (e) {
      setActionError((e as Error).message)
    }
  }

  const rangeControl = (
    <div className="segmented" role="radiogroup" aria-label="Time range">
      {RANGES.map((r) => (
        <label className="chip" key={r.days}>
          <input type="radio" name="range" checked={days === r.days} onChange={() => setDays(r.days)} />
          {r.label}
        </label>
      ))}
    </div>
  )

  if (error) return <div className="alert alert-danger">{error}</div>

  const head = (
    <div className="page-head">
      <div>
        <h1>Progress</h1>
        <p className="muted">Your weight trend and how your eating compares to your target.</p>
      </div>
      {rangeControl}
    </div>
  )

  if (!data) {
    return (
      <div className="stack">
        {head}
        <div className="loading">Loading your progress…</div>
      </div>
    )
  }

  const [profile, weights, history] = data
  const goal = profile.metrics.effective_goal
  const latest = weights.at(-1)
  const change = weights.length > 1 ? latest!.weight_kg - weights[0].weight_kg : null
  const logged = history.days.filter((d) => d.calories > 0)
  const avg = logged.length ? logged.reduce((s, d) => s + d.calories, 0) / logged.length : null

  return (
    <div className="stack" style={{ opacity: loading ? 0.6 : 1, transition: 'opacity 0.2s' }}>
      {head}
      {actionError && <div className="alert alert-danger">{actionError}</div>}

      <div className="grid grid-4">
        <div className="card">
          <span className="stat-label">Current weight</span>
          <div className="stat-value">
            {latest?.weight_kg ?? profile.weight_kg}
            <small>kg</small>
          </div>
          <p className="stat-sub">{latest ? `Logged ${shortDate(latest.date)}` : 'From your profile'}</p>
        </div>
        <div className="card">
          <span className="stat-label">Change over {days} days</span>
          <div className={`stat-value ${change !== null ? deltaClass(change, goal) : ''}`}>
            {change === null ? '—' : `${change > 0 ? '+' : change < 0 ? '−' : ''}${Math.abs(change).toFixed(1)}`}
            {change !== null && <small>kg</small>}
          </div>
          <p className="stat-sub">{change === null ? 'Log at least two weigh-ins' : `${weights.length} weigh-ins`}</p>
        </div>
        <div className="card">
          <span className="stat-label">Average daily intake</span>
          <div className="stat-value">
            {avg === null ? '—' : fmt(avg)}
            {avg !== null && <small>kcal</small>}
          </div>
          <p className="stat-sub">Target {fmt(history.target_calories)} kcal</p>
        </div>
        <div className="card">
          <span className="stat-label">Days with food logged</span>
          <div className="stat-value">
            {logged.length}
            <small>/ {days}</small>
          </div>
          <p className="stat-sub">Consistency beats perfection</p>
        </div>
      </div>

      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <section className="card stack">
          <div>
            <h2>Weight (kg)</h2>
            <p className="small muted">
              Shaded area is your healthy range: {profile.metrics.healthy_weight_range_kg[0]}–
              {profile.metrics.healthy_weight_range_kg[1]} kg.
            </p>
          </div>
          <LineChart
            label="Weight over time"
            points={weights.map((w) => ({ date: w.date, value: w.weight_kg }))}
            band={profile.metrics.healthy_weight_range_kg}
            format={(v) => `${v} kg`}
          />
          <LogWeight onSaved={reload} initial={latest?.weight_kg ?? profile.weight_kg} />
          {weights.length > 0 && (
            <DataTable
              columns={['Date', 'Weight (kg)']}
              rows={weights.map((w) => [shortDate(w.date), w.weight_kg])}
            />
          )}
        </section>

        <section className="card stack">
          <div>
            <h2>Daily calories (kcal)</h2>
            <p className="small muted">Total logged per day against your target.</p>
          </div>
          {logged.length === 0 ? (
            <div className="chart-empty">No meals logged in this period yet.</div>
          ) : (
            <ColumnChart
              label="Calories logged per day"
              points={history.days.map((d) => ({ date: d.date, value: d.calories }))}
              target={history.target_calories}
              format={(v) => `${fmt(v)} kcal`}
            />
          )}
          <DataTable
            columns={['Date', 'Calories', 'Protein (g)', 'Carbs (g)', 'Fat (g)']}
            rows={history.days.map((d) => [shortDate(d.date), fmt(d.calories), d.protein_g, d.carbs_g, d.fat_g])}
          />
        </section>
      </div>

      {weights.length > 0 && (
        <section className="card">
          <h2 style={{ marginBottom: 8 }}>Recent weigh-ins</h2>
          <ul className="list">
            {weights
              .slice(-8)
              .reverse()
              .map((w) => (
                <li key={w.id}>
                  <span className="list-main">{shortDate(w.date)}</span>
                  <span className="list-end">{w.weight_kg} kg</span>
                  <button
                    type="button"
                    className="btn btn-ghost btn-icon"
                    onClick={() => remove(w.id)}
                    aria-label={`Delete weigh-in from ${shortDate(w.date)}`}
                  >
                    <TrashIcon />
                  </button>
                </li>
              ))}
          </ul>
        </section>
      )}
    </div>
  )
}
