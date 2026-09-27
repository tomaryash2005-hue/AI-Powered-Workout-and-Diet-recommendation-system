import { useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../useAuth'
import { BmiScale, BmiTag, MacroBar, Ring, Warnings } from '../components/Progress'
import { fmt, GOAL_LABELS, today, todayWeekday, useAsync } from '../utils'

export default function Dashboard() {
  const { user } = useAuth()
  const day = today()
  const { data, error } = useAsync(
    useCallback(() => Promise.all([api.getProfile(), api.summary(day), api.workoutPlan(day)]), [day]),
  )

  if (error) return <div className="alert alert-danger">{error}</div>
  if (!data) return <div className="loading">Loading your dashboard…</div>

  const [profile, summary, workout] = data
  const m = profile.metrics
  const session = workout.week.find((d) => d.day === todayWeekday())

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Hi, {user?.name.split(' ')[0]}</h1>
          <p className="muted">
            Goal: {GOAL_LABELS[m.effective_goal]} · {fmt(m.target_calories)} kcal/day
          </p>
        </div>
        <Link to="/meals" className="btn btn-primary">
          Log a meal
        </Link>
      </div>

      <Warnings metrics={m} />

      <div className="grid grid-4">
        <div className="card">
          <div className="spread">
            <span className="stat-label">BMI</span>
            <BmiTag bmi={m.bmi} />
          </div>
          <div className="stat-value">{m.bmi}</div>
          <BmiScale bmi={m.bmi} />
        </div>
        <div className="card">
          <span className="stat-label">Daily calorie target</span>
          <div className="stat-value">
            {fmt(m.target_calories)}
            <small>kcal</small>
          </div>
          <p className="stat-sub">Maintenance: {fmt(m.tdee)} kcal</p>
        </div>
        <div className="card">
          <span className="stat-label">Healthy weight range</span>
          <div className="stat-value">
            {m.healthy_weight_range_kg[0]}–{m.healthy_weight_range_kg[1]}
            <small>kg</small>
          </div>
          <p className="stat-sub">You: {profile.weight_kg} kg</p>
        </div>
        <div className="card">
          <span className="stat-label">Water</span>
          <div className="stat-value">
            {m.water_liters}
            <small>L / day</small>
          </div>
          <p className="stat-sub">≈ {Math.round(m.water_liters / 0.25)} glasses</p>
        </div>
      </div>

      <div className="grid grid-2">
        <section className="card">
          <div className="card-head">
            <h2>Today's nutrition</h2>
            <Link to="/meals" className="small">
              Food log →
            </Link>
          </div>
          <div className="row" style={{ gap: 24, alignItems: 'center', flexWrap: 'wrap' }}>
            <Ring progress={summary.calories} />
            <div className="stack" style={{ flex: 1, minWidth: 180, gap: 12 }}>
              <p className="small muted num">
                {fmt(summary.calories.consumed)} of {fmt(summary.calories.target)} kcal eaten
              </p>
              <MacroBar label="Protein" progress={summary.protein_g} color="var(--protein)" />
              <MacroBar label="Carbs" progress={summary.carbs_g} color="var(--carbs)" />
              <MacroBar label="Fat" progress={summary.fat_g} color="var(--fat)" />
            </div>
          </div>
        </section>

        <section className="card">
          <div className="card-head">
            <h2>Today's workout</h2>
            <Link to="/workout" className="small">
              Full week →
            </Link>
          </div>
          {session ? (
            <>
              <div className="spread">
                <strong>{session.title}</strong>
                <span className="tag">{session.duration_min} min</span>
              </div>
              <ul className="list" style={{ marginTop: 8 }}>
                {session.exercises.map((e) => (
                  <li key={e.name}>
                    <span className="list-main">{e.name}</span>
                    <span className="list-end muted small">
                      {e.sets > 1 ? `${e.sets} × ${e.reps}` : e.reps}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="empty">No session found for today.</p>
          )}
        </section>
      </div>

      <p className="disclaimer">
        FitAI gives general wellness guidance, not medical advice. Consult a healthcare professional before
        making major changes to your diet or exercise routine.
      </p>
    </div>
  )
}
