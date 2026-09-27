import { useCallback, useState, type CSSProperties } from 'react'
import { api, type DietPlan, type MealType, type PlannedItem, type PlannedMeal } from '../api'
import DateNav from '../components/DateNav'
import { fmt, MEAL_LABELS, today, useAsync } from '../utils'

function servingsLabel(servings: number, serving: string) {
  return servings === 1 ? serving : `${servings} × ${serving}`
}

interface SwapTarget {
  mealType: MealType
  slot: number
}

function SwapPanel({
  day,
  target,
  onSwapped,
  onClose,
}: {
  day: string
  target: SwapTarget
  onSwapped: (plan: DietPlan) => void
  onClose: () => void
}) {
  const { mealType, slot } = target
  const { data: options, error } = useAsync(
    useCallback(() => api.alternatives(day, mealType, slot), [day, mealType, slot]),
  )
  const [busy, setBusy] = useState(false)
  const [swapError, setSwapError] = useState<string | null>(null)

  const choose = async (item: PlannedItem) => {
    setBusy(true)
    setSwapError(null)
    try {
      onSwapped(await api.swapDish(day, mealType, slot, item.food_id))
    } catch (e) {
      setSwapError((e as Error).message)
      setBusy(false)
    }
  }

  return (
    <div className="swap-panel stack" style={{ gap: 8 }}>
      <div className="spread">
        <span className="small">
          <strong>Swap for</strong> <span className="muted">— portions adjusted to the same calories</span>
        </span>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
          Cancel
        </button>
      </div>
      {error && <div className="alert alert-danger">{error}</div>}
      {swapError && <div className="alert alert-danger">{swapError}</div>}
      {!options && !error && <p className="small muted">Finding alternatives…</p>}
      {options && options.length === 0 && (
        <p className="small muted">No other foods fit this spot with your diet and allergies.</p>
      )}
      {options && options.length > 0 && (
        <div className="search-results" aria-label="Alternatives">
          {options.map((o) => (
            <button type="button" key={o.food_id} disabled={busy} onClick={() => choose(o)}>
              <span>
                <strong>{o.name}</strong>
                <span className="small muted"> · {servingsLabel(o.servings, o.serving)}</span>
              </span>
              <span className="small muted num list-end">
                {fmt(o.calories)} kcal
                <br />
                {Math.round(o.protein_g)} g protein
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function DietPage() {
  const [day, setDay] = useState(today())
  const [logged, setLogged] = useState<Record<string, 'saving' | 'done'>>({})
  const [actionError, setActionError] = useState<string | null>(null)
  const [swapTarget, setSwapTarget] = useState<SwapTarget | null>(null)
  const [updated, setUpdated] = useState<DietPlan | null>(null)
  const { data: fetched, error } = useAsync(useCallback(() => api.dietPlan(day), [day]))
  const { data: options } = useAsync(api.options)

  // Swap and reset calls return the updated plan, which replaces the fetched one for that day.
  const plan = updated?.date === day ? updated : fetched
  const labelFor = (key: string) => options?.allergens.find((a) => a.key === key)?.label ?? key
  const dietLabel = options?.diet_types.find((d) => d.key === plan?.diet_type)?.label.split(' (')[0]

  const changeDay = (d: string) => {
    setSwapTarget(null)
    setDay(d)
  }

  const applyPlan = (p: DietPlan) => {
    setUpdated(p)
    setSwapTarget(null)
  }

  const resetSwaps = async () => {
    setActionError(null)
    try {
      applyPlan(await api.resetSwaps(day))
    } catch (e) {
      setActionError((e as Error).message)
    }
  }

  const logMeal = async (meal: PlannedMeal) => {
    const key = `${day}-${meal.meal_type}`
    setActionError(null)
    setLogged((l) => ({ ...l, [key]: 'saving' }))
    try {
      for (const item of meal.items) {
        await api.logMeal({ date: day, meal_type: meal.meal_type, food_id: item.food_id, servings: item.servings })
      }
      setLogged((l) => ({ ...l, [key]: 'done' }))
    } catch (e) {
      setActionError((e as Error).message)
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
        <DateNav value={day} onChange={changeDay} />
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {actionError && <div className="alert alert-danger">{actionError}</div>}
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
            <div className="row" style={{ marginTop: 12 }}>
              {dietLabel && <span className="tag tag-accent">{dietLabel}</span>}
              {plan.excluded_allergens.length > 0 && (
                <>
                  <span className="small muted">Excluded for your allergies:</span>
                  {plan.excluded_allergens.map((a) => (
                    <span key={a} className="tag tag-danger">
                      {labelFor(a)}
                    </span>
                  ))}
                </>
              )}
              {plan.has_swaps && (
                <button
                  type="button"
                  className="btn btn-sm btn-ghost"
                  style={{ marginLeft: 'auto' }}
                  onClick={resetSwaps}
                >
                  Undo my swaps
                </button>
              )}
            </div>
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
                    {meal.items.map((item) => {
                      const open = swapTarget?.mealType === meal.meal_type && swapTarget.slot === item.slot
                      return (
                        <li key={item.slot} style={{ flexWrap: 'wrap' }}>
                          <div className="list-main">
                            <strong>{item.name}</strong>
                            {item.swapped && (
                              <span className="tag" style={{ marginLeft: 6 }}>
                                Swapped
                              </span>
                            )}
                            <div className="small muted">{servingsLabel(item.servings, item.serving)}</div>
                          </div>
                          <div className="list-end small">
                            <div>{fmt(item.calories)} kcal</div>
                            <div className="muted">{Math.round(item.protein_g)} g protein</div>
                          </div>
                          <button
                            type="button"
                            className="btn btn-sm"
                            aria-expanded={open}
                            aria-label={`Swap ${item.name}`}
                            onClick={() => setSwapTarget(open ? null : { mealType: meal.meal_type, slot: item.slot })}
                          >
                            Swap
                          </button>
                          {open && (
                            <div style={{ flexBasis: '100%' }}>
                              <SwapPanel
                                day={day}
                                target={swapTarget}
                                onSwapped={applyPlan}
                                onClose={() => setSwapTarget(null)}
                              />
                            </div>
                          )}
                        </li>
                      )
                    })}
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
