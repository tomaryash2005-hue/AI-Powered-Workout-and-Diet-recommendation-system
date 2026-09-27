import { useCallback, useState, type FormEvent } from 'react'
import { api, type Workout, type WorkoutDay, type WorkoutSet } from '../api'
import { CheckIcon, ChevronDown } from '../components/Icons'
import { EQUIPMENT_LABELS, shiftDate, today, todayWeekday, useAsync } from '../utils'

interface SetRow {
  exercise: string
  set_number: number
  timed: boolean
  reps: string
  weight: string
}

const firstNumber = (text: string) => text.match(/\d+/)?.[0] ?? ''

function initialRows(day: WorkoutDay): SetRow[] {
  return day.exercises.flatMap((e) => {
    const timed = e.reps.trim().endsWith('s')
    return Array.from({ length: e.sets }, (_, i) => ({
      exercise: e.name,
      set_number: i + 1,
      timed,
      reps: firstNumber(e.reps),
      weight: '',
    }))
  })
}

function LogWorkout({
  day,
  date,
  onSaved,
  onCancel,
}: {
  day: WorkoutDay
  date: string
  onSaved: () => void
  onCancel: () => void
}) {
  const cardio = day.focus === 'cardio'
  const [rows, setRows] = useState<SetRow[]>(() => (cardio ? [] : initialRows(day)))
  const [minutes, setMinutes] = useState(String(day.duration_min))
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const update = (index: number, key: 'reps' | 'weight', value: string) =>
    setRows((r) => r.map((row, i) => (i === index ? { ...row, [key]: value } : row)))

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    const sets: WorkoutSet[] = rows.map((r) => ({
      exercise: r.exercise,
      set_number: r.set_number,
      reps: r.timed || r.reps === '' ? null : Number(r.reps),
      duration_s: r.timed && r.reps !== '' ? Number(r.reps) : null,
      weight_kg: r.weight === '' ? null : Number(r.weight),
    }))
    try {
      await api.logWorkout({
        date,
        title: day.title,
        duration_min: minutes === '' ? null : Number(minutes),
        notes: null,
        sets,
      })
      onSaved()
    } catch (err) {
      setError((err as Error).message)
      setBusy(false)
    }
  }

  return (
    <form className="log-panel stack" style={{ gap: 10 }} onSubmit={submit}>
      <label className="field" style={{ maxWidth: 160 }}>
        <span>Duration (min)</span>
        <input
          className="input"
          type="number"
          inputMode="numeric"
          min={0}
          max={600}
          value={minutes}
          onChange={(e) => setMinutes(e.target.value)}
        />
      </label>
      {rows.length > 0 && (
        <div className="set-grid">
          <span className="small muted">Set</span>
          <span className="small muted">Reps / sec</span>
          <span className="small muted">Weight (kg)</span>
          {rows.map((r, i) => {
            const header = i === 0 || rows[i - 1].exercise !== r.exercise
            return (
              <div key={`${r.exercise}-${r.set_number}`} style={{ display: 'contents' }}>
                {header && (
                  <strong className="set-label" style={{ gridColumn: '1 / -1', marginTop: 6 }}>
                    {r.exercise}
                  </strong>
                )}
                <span className="set-label muted">Set {r.set_number}</span>
                <input
                  className="input"
                  type="number"
                  inputMode="numeric"
                  min={0}
                  max={1000}
                  aria-label={`${r.exercise} set ${r.set_number} ${r.timed ? 'seconds' : 'reps'}`}
                  placeholder={r.timed ? 'sec' : 'reps'}
                  value={r.reps}
                  onChange={(e) => update(i, 'reps', e.target.value)}
                />
                <input
                  className="input"
                  type="number"
                  inputMode="decimal"
                  min={0}
                  max={1000}
                  step="0.5"
                  aria-label={`${r.exercise} set ${r.set_number} weight`}
                  placeholder={r.timed ? '—' : 'kg'}
                  disabled={r.timed}
                  value={r.weight}
                  onChange={(e) => update(i, 'weight', e.target.value)}
                />
              </div>
            )
          })}
        </div>
      )}
      {!cardio && (
        <p className="small muted">Leave weight empty for bodyweight exercises. Adjust reps to what you actually did.</p>
      )}
      {error && <div className="alert alert-danger">{error}</div>}
      <div className="row">
        <button className="btn btn-primary btn-sm" disabled={busy}>
          {busy ? 'Saving…' : 'Save workout'}
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  )
}

export default function WorkoutPage() {
  const now = today()
  const current = todayWeekday()
  const { data: plan, error } = useAsync(useCallback(() => api.workoutPlan(now), [now]))
  const monday = shiftDate(now, -((new Date().getDay() + 6) % 7))
  const { data: logs, reload } = useAsync(useCallback(() => api.workouts(shiftDate(monday, 6), 7), [monday]))
  const [logging, setLogging] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  if (error) return <div className="alert alert-danger">{error}</div>
  if (!plan) return <div className="loading">Building your workout plan…</div>

  const logsOn = (date: string): Workout[] => logs?.filter((l) => l.date === date) ?? []
  const done = plan.week.filter((d, i) => d.focus !== 'rest' && logsOn(shiftDate(monday, i)).length > 0).length

  const undo = async (id: number) => {
    setActionError(null)
    try {
      await api.deleteWorkout(id)
      reload()
    } catch (e) {
      setActionError((e as Error).message)
    }
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Workout plan</h1>
          <p className="muted">
            {plan.days_per_week} training days this week · {plan.level} level ·{' '}
            {EQUIPMENT_LABELS[plan.equipment]}
            {plan.low_impact && ' · low impact'}
          </p>
        </div>
        <span className="tag tag-accent" style={{ fontSize: '0.85rem', padding: '4px 12px' }}>
          {done} / {plan.days_per_week} done this week
        </span>
      </div>
      {actionError && <div className="alert alert-danger">{actionError}</div>}

      <div className="week">
        {plan.week.map((d, i) => {
          const date = shiftDate(monday, i)
          const isToday = d.day === current
          const isRest = d.focus === 'rest'
          const logged = logsOn(date)
          const canLog = !isRest && date <= now && logged.length === 0
          return (
            <details
              key={d.day}
              className={`card day-card${isToday ? ' today' : ''}${isRest ? ' rest' : ''}`}
              open={isToday}
            >
              <summary className="spread">
                <div>
                  <div className="row">
                    <strong>{d.day}</strong>
                    {isToday && <span className="tag tag-accent">Today</span>}
                    {logged.length > 0 && (
                      <span className="tag tag-accent">
                        <CheckIcon /> Done
                      </span>
                    )}
                  </div>
                  <div className="small muted">
                    {d.title} · {d.duration_min} min
                  </div>
                </div>
                <ChevronDown className="chevron" />
              </summary>
              <table className="exercise-table">
                <thead>
                  <tr>
                    <th>Exercise</th>
                    <th>Sets × reps</th>
                    <th className="rest-col">Rest</th>
                  </tr>
                </thead>
                <tbody>
                  {d.exercises.map((e) => (
                    <tr key={e.name}>
                      <td>
                        <strong>{e.name}</strong>
                        <div className="small muted">{e.tip}</div>
                      </td>
                      <td className="num">{e.sets > 1 ? `${e.sets} × ${e.reps}` : e.reps}</td>
                      <td className="num muted rest-col">{e.rest_seconds ? `${e.rest_seconds} s` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {logged.map((l) => (
                <div key={l.id} className="spread small" style={{ marginTop: 10 }}>
                  <span className="muted">
                    Logged {l.duration_min ? `${l.duration_min} min` : ''}
                    {l.sets.some((s) => s.weight_kg) &&
                      ` · top set ${Math.max(...l.sets.map((s) => s.weight_kg ?? 0))} kg`}
                  </span>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => undo(l.id)}>
                    Undo
                  </button>
                </div>
              ))}
              {canLog &&
                (logging === date ? (
                  <LogWorkout
                    day={d}
                    date={date}
                    onCancel={() => setLogging(null)}
                    onSaved={() => {
                      setLogging(null)
                      reload()
                    }}
                  />
                ) : (
                  <button type="button" className="btn btn-sm" style={{ marginTop: 12 }} onClick={() => setLogging(date)}>
                    <CheckIcon /> Log this workout
                  </button>
                ))}
            </details>
          )
        })}
      </div>

      <section className="card">
        <h2 style={{ marginBottom: 10 }}>How to use this plan</h2>
        <ul className="tips">
          {plan.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}
