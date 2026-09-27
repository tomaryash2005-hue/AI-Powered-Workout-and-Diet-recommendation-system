import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, type Food, type MealLog, type MealType } from '../api'
import AiMealLogger from '../components/AiMealLogger'
import DateNav from '../components/DateNav'
import { AlertIcon, PlusIcon, TrashIcon } from '../components/Icons'
import { MacroBar, Ring } from '../components/Progress'
import { defaultMealType, fmt, MEAL_LABELS, MEAL_TYPES, today, useAsync } from '../utils'

type Mode = 'ai' | 'search' | 'custom'

const MODE_LABELS: Record<Mode, string> = { ai: 'Describe', search: 'Search', custom: 'Custom' }

const EMPTY_CUSTOM = { name: '', calories: '', protein_g: '', carbs_g: '', fat_g: '' }

function AddFood({ day, onAdded }: { day: string; onAdded: (m: MealLog) => void }) {
  const [mealType, setMealType] = useState<MealType>(defaultMealType())
  const { data: options } = useAsync(api.options)
  const [chosenMode, setMode] = useState<Mode | null>(null)
  // Default to AI logging when the server has it turned on.
  const mode: Mode = chosenMode ?? (options?.ai_logging ? 'ai' : 'search')
  const modes: Mode[] = options?.ai_logging ? ['ai', 'search', 'custom'] : ['search', 'custom']
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Food[]>([])
  const [selected, setSelected] = useState<Food | null>(null)
  const [servings, setServings] = useState('1')
  const [custom, setCustom] = useState(EMPTY_CUSTOM)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (mode !== 'search') return
    const handle = setTimeout(() => {
      api.searchFoods(query).then(setResults).catch(() => setResults([]))
    }, 200)
    return () => clearTimeout(handle)
  }, [query, mode])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const meal =
        mode === 'search'
          ? await api.logMeal({ date: day, meal_type: mealType, food_id: selected!.id, servings: Number(servings) })
          : await api.logMeal({
              date: day,
              meal_type: mealType,
              name: custom.name,
              calories: Number(custom.calories),
              protein_g: Number(custom.protein_g || 0),
              carbs_g: Number(custom.carbs_g || 0),
              fat_g: Number(custom.fat_g || 0),
              allergens: [],
            })
      onAdded(meal)
      setSelected(null)
      setServings('1')
      setCustom(EMPTY_CUSTOM)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const servingsNum = Number(servings)

  return (
    <form className="card stack" onSubmit={submit}>
      <div className="spread">
        <h2>Add food</h2>
        <div
          className="tabs"
          style={{ margin: 0, minWidth: modes.length * 96, gridTemplateColumns: `repeat(${modes.length}, 1fr)` }}
          role="tablist"
        >
          {modes.map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={mode === m}
              className={mode === m ? 'active' : ''}
              onClick={() => setMode(m)}
            >
              {MODE_LABELS[m]}
            </button>
          ))}
        </div>
      </div>

      <div className="segmented" role="radiogroup" aria-label="Meal">
        {MEAL_TYPES.map((t) => (
          <label className="chip" key={t}>
            <input type="radio" name="meal_type" checked={mealType === t} onChange={() => setMealType(t)} />
            {MEAL_LABELS[t]}
          </label>
        ))}
      </div>

      {mode === 'ai' ? (
        <AiMealLogger day={day} mealType={mealType} onAdded={onAdded} />
      ) : mode === 'search' ? (
        <>
          <input
            className="input"
            type="search"
            placeholder="Search foods, e.g. dal, paneer, chicken…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search foods"
          />
          <div className="search-results">
            {results.length === 0 && <div className="empty small">No foods match — try a custom entry.</div>}
            {results.map((f) => (
              <button
                type="button"
                key={f.id}
                className={selected?.id === f.id ? 'selected' : ''}
                onClick={() => setSelected(f)}
              >
                <span>
                  <strong>{f.name}</strong>
                  <span className="small muted"> · {f.serving}</span>
                  {f.conflicts_with_allergies.length > 0 && (
                    <span className="tag tag-danger" style={{ marginLeft: 6 }}>
                      Allergen
                    </span>
                  )}
                  {!f.fits_diet && (
                    <span className="tag tag-warn" style={{ marginLeft: 6 }}>
                      Not in your diet
                    </span>
                  )}
                  {f.source === 'usda' && (
                    <span className="tag" style={{ marginLeft: 6 }}>
                      USDA
                    </span>
                  )}
                </span>
                <span className="small muted num">{fmt(f.calories)} kcal</span>
              </button>
            ))}
          </div>
          {selected && (
            <div className="stack" style={{ gap: 10 }}>
              {selected.conflicts_with_allergies.length > 0 && (
                <div className="alert alert-danger">
                  <AlertIcon />
                  <span>
                    <strong>{selected.name}</strong> contains {selected.conflicts_with_allergies.join(', ')}, which
                    you listed as an allergy.
                  </span>
                </div>
              )}
              {!selected.fits_diet && (
                <div className="alert alert-warn">
                  <AlertIcon />
                  <span>
                    <strong>{selected.name}</strong> doesn't match the diet type in your profile.
                  </span>
                </div>
              )}
              {selected.source === 'usda' && (
                <p className="small muted">
                  Nutrition from USDA FoodData Central, per 100 g. Allergens are estimated from the name and
                  ingredients — always check the label.
                </p>
              )}
              <div className="row" style={{ alignItems: 'flex-end' }}>
                <label className="field" style={{ width: 120 }}>
                  <span>Servings</span>
                  <input
                    className="input"
                    type="number"
                    inputMode="decimal"
                    min={0.25}
                    max={20}
                    step={0.25}
                    value={servings}
                    onChange={(e) => setServings(e.target.value)}
                    required
                  />
                </label>
                <p className="small muted num" style={{ paddingBottom: 10 }}>
                  = {fmt(selected.calories * (servingsNum || 0))} kcal ·{' '}
                  {Math.round(selected.protein_g * (servingsNum || 0))} g protein
                </p>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="form-grid">
          <label className="field" style={{ gridColumn: '1 / -1' }}>
            <span>Food name</span>
            <input
              className="input"
              value={custom.name}
              maxLength={120}
              onChange={(e) => setCustom({ ...custom, name: e.target.value })}
              required
            />
          </label>
          {(
            [
              ['calories', 'Calories (kcal)', true],
              ['protein_g', 'Protein (g)', false],
              ['carbs_g', 'Carbs (g)', false],
              ['fat_g', 'Fat (g)', false],
            ] as const
          ).map(([key, label, required]) => (
            <label className="field" key={key}>
              <span>{label}</span>
              <input
                className="input"
                type="number"
                inputMode="decimal"
                min={0}
                step="any"
                value={custom[key]}
                onChange={(e) => setCustom({ ...custom, [key]: e.target.value })}
                required={required}
              />
            </label>
          ))}
        </div>
      )}

      {error && <div className="alert alert-danger">{error}</div>}
      {mode !== 'ai' && (
        <button className="btn btn-primary" disabled={busy || (mode === 'search' && !selected)}>
          <PlusIcon />
          Add to {MEAL_LABELS[mealType].toLowerCase()}
        </button>
      )}
    </form>
  )
}

export default function MealsPage() {
  const [day, setDay] = useState(today())
  const { data: summary, error, reload } = useAsync(useCallback(() => api.summary(day), [day]))

  const [deleteError, setDeleteError] = useState<string | null>(null)

  const remove = async (id: number) => {
    setDeleteError(null)
    try {
      await api.deleteMeal(id)
      reload()
    } catch (e) {
      setDeleteError((e as Error).message)
    }
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Food log</h1>
          <p className="muted">Track what you eat and see how it compares to your targets.</p>
        </div>
        <DateNav value={day} onChange={setDay} />
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {deleteError && <div className="alert alert-danger">{deleteError}</div>}

      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <div className="stack">
          {summary && (
            <section className="card">
              <div className="row" style={{ gap: 24, alignItems: 'center' }}>
                <Ring progress={summary.calories} />
                <div className="stack" style={{ flex: 1, minWidth: 180, gap: 12 }}>
                  <p className="small muted num">
                    {fmt(summary.calories.consumed)} of {fmt(summary.calories.target)} kcal
                  </p>
                  <MacroBar label="Protein" progress={summary.protein_g} color="var(--protein)" />
                  <MacroBar label="Carbs" progress={summary.carbs_g} color="var(--carbs)" />
                  <MacroBar label="Fat" progress={summary.fat_g} color="var(--fat)" />
                </div>
              </div>
            </section>
          )}
          <AddFood day={day} onAdded={reload} />
        </div>

        <div className="stack">
          {summary &&
            MEAL_TYPES.map((type) => {
              const entries = summary.meals.filter((m) => m.meal_type === type)
              const total = entries.reduce((s, m) => s + m.calories, 0)
              return (
                <section className="card" key={type}>
                  <div className="card-head" style={{ marginBottom: entries.length ? 4 : 0 }}>
                    <h2>{MEAL_LABELS[type]}</h2>
                    <span className="muted small num">{fmt(total)} kcal</span>
                  </div>
                  {entries.length === 0 ? (
                    <p className="small muted">Nothing logged yet.</p>
                  ) : (
                    <ul className="list">
                      {entries.map((m) => (
                        <li key={m.id}>
                          <div className="list-main">
                            <strong>{m.name}</strong>
                            <div className="small muted">
                              {m.food_id ? `${m.servings} serving${m.servings === 1 ? '' : 's'} · ` : ''}P{' '}
                              {Math.round(m.protein_g)} · C {Math.round(m.carbs_g)} · F {Math.round(m.fat_g)}
                            </div>
                            {m.allergy_warning.length > 0 && (
                              <span className="tag tag-danger" style={{ marginTop: 4 }}>
                                Contains your allergen: {m.allergy_warning.join(', ')}
                              </span>
                            )}
                          </div>
                          <span className="list-end small">{fmt(m.calories)} kcal</span>
                          <button
                            type="button"
                            className="btn btn-ghost btn-icon"
                            onClick={() => remove(m.id)}
                            aria-label={`Delete ${m.name}`}
                          >
                            <TrashIcon />
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              )
            })}
        </div>
      </div>
    </div>
  )
}
