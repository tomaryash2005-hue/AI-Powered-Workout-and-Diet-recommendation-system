import { useCallback } from 'react'
import { api } from '../api'
import { ChevronDown } from '../components/Icons'
import { today, todayWeekday, useAsync } from '../utils'

export default function WorkoutPage() {
  const { data: plan, error } = useAsync(useCallback(() => api.workoutPlan(today()), []))
  const current = todayWeekday()

  if (error) return <div className="alert alert-danger">{error}</div>
  if (!plan) return <div className="loading">Building your workout plan…</div>

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Workout plan</h1>
          <p className="muted">
            {plan.days_per_week} training days this week · {plan.level} level
            {plan.low_impact && ' · low impact'}
          </p>
        </div>
      </div>

      <div className="week">
        {plan.week.map((d) => {
          const isToday = d.day === current
          const isRest = d.focus === 'rest'
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
