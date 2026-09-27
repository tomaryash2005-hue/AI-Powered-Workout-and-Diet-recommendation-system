import { useCallback, useState, type CSSProperties } from 'react'
import { api, type PlannedMeal } from '../api'
import DateNav from '../components/DateNav'
import { fmt, MEAL_LABELS, today, useAsync } from '../utils'

function servingsLabel(servings: number, serving: string) {
  return servings === 1 ? serving : `${servings} × ${serving}`
}

export default function DietPage() {
  const [day, setDay] = useState(today())
  const [logged, setLogged] = useState<Record<string, 'saving' | 'done'>>({})
  const [logError, setLogError] = useState<string | null>(null)
  const { data: plan, error } = useAsync(useCallback(() => api.dietPlan(day), [day]))
  const { data: allergens } = useAsync(api.allergens)

  const labelFor = (key: string) => allergens?.find((a) => a.key === key)?.label ?? key

  const logMeal = async (meal: PlannedMeal) => {
    const key = `${day}-${meal.meal_type}`
    setLogError(null)
    setLogged((l) => ({ ...l, [key]: 'saving' }))
    try {
      for (const item of meal.items) {
        await api.logMeal({ date: day, meal_type: meal.meal_type, food_id: item.food_id, servings: item.servings })
      }
      setLogged((l) => ({ ...l, [key]: 'done' }))
    } catch (e) {
      setLogError((e as Error).message)
      setLogged((l) => {
        const next = { ...l }
        delete next[key]
        return next
      })
    }
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Diet plan</h1>
          <p className="muted">A balanced day of meals matched to your calorie and protein targets.</p>
        </div>
        <DateNav value={day} onChange={setDay} />
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {logError && <div className="alert alert-danger">{logError}</div>}
      {!plan && !error && <div className="loading">Building your plan…</div>}

      {plan && (
        <>
          <div className="card">
            <div className="spread" style={{ flexWrap: 'wrap' }}>
              <div>
                <span className="stat-label">Planned for the day</span>
                <div className="stat-value">
                  {fmt(plan.calories)}
                  <small>/ {fmt(plan.target_calories)} kcal target</small>
                </div>
              </div>
              <div className="macro-dots">
                <span style={{ '--dot': 'var(--protein)' } as CSSProperties}>Protein {plan.protein_g} g</span>
                <span style={{ '--dot': 'var(--carbs)' } as CSSProperties}>Carbs {plan.carbs_g} g</span>
                <span style={{ '--dot': 'var(--fat)' } as CSSProperties}>Fat {plan.fat_g} g</span>
              </div>
            </div>
            {plan.excluded_allergens.length > 0 && (
              <div className="row" style={{ marginTop: 12 }}>
                <span className="small muted">Excluded for your allergies:</span>
                {plan.excluded_allergens.map((a) => (
                  <span key={a} className="tag tag-danger">
                    {labelFor(a)}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-2">
            {plan.meals.map((meal) => {
              const state = logged[`${day}-${meal.meal_type}`]
              return (
                <section className="card" key={meal.meal_type}>
                  <div className="card-head">
                    <h2>{MEAL_LABELS[meal.meal_type]}</h2>
                    <span className="muted small num">{fmt(meal.calories)} kcal</span>
                  </div>
                  <ul className="list">
                    {meal.items.map((item) => (
                      <li key={item.food_id}>
                        <div className="list-main">
                          <strong>{item.name}</strong>
                          <div className="small muted">{servingsLabel(item.servings, item.serving)}</div>
                        </div>
                        <div className="list-end small">
                          <div>{fmt(item.calories)} kcal</div>
                          <div className="muted">{Math.round(item.protein_g)} g protein</div>
                        </div>
                      </li>
                    ))}
                  </ul>
                  <button
                    type="button"
                    className="btn btn-sm"
                    style={{ marginTop: 12 }}
                    disabled={state !== undefined}
                    onClick={() => logMeal(meal)}
                  >
                    {state === 'done' ? 'Logged ✓' : state === 'saving' ? 'Logging…' : 'I ate this — log it'}
                  </button>
                </section>
              )
            })}
          </div>

          <section className="card">
            <h2 style={{ marginBottom: 10 }}>Tips for you</h2>
            <ul className="tips">
              {plan.tips.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  )
}
