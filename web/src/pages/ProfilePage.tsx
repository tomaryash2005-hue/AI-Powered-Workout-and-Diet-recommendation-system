import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  api,
  ApiError,
  type ActivityLevel,
  type BmiStandard,
  type DietType,
  type Equipment,
  type Goal,
  type Options,
  type ProfileInput,
  type Sex,
} from '../api'
import { BmiScale, BmiTag } from '../components/Progress'
import { useAuth } from '../useAuth'
import { ACTIVITY_LABELS, BMI_CUTOFFS, bmiCategory, bmiFrom, GOAL_LABELS, today } from '../utils'

interface FormState {
  age: string
  sex: Sex
  height_cm: string
  weight_kg: string
  activity_level: ActivityLevel
  goal: Goal
  allergies: string[]
  diet_type: DietType
  bmi_standard: BmiStandard
  equipment: Equipment
}

const EMPTY: FormState = {
  age: '',
  sex: 'female',
  height_cm: '',
  weight_kg: '',
  activity_level: 'light',
  goal: 'maintain',
  allergies: [],
  diet_type: 'vegetarian',
  bmi_standard: 'who',
  equipment: 'none',
}

const DIET_HINTS: Record<DietType, string> = {
  non_vegetarian: 'Everything, including chicken, meat, fish and eggs',
  pescatarian: 'Fish and seafood, eggs and dairy — no meat',
  eggetarian: 'Vegetarian food plus eggs',
  vegetarian: 'No meat, fish or eggs — dairy is fine',
  vegan: 'Only plant foods — no dairy, eggs, meat or fish',
}

export default function ProfilePage() {
  const { user, markProfileComplete } = useAuth()
  const navigate = useNavigate()
  const onboarding = !user?.has_profile
  const [form, setForm] = useState<FormState>(EMPTY)
  const [options, setOptions] = useState<Options | null>(null)
  const [loaded, setLoaded] = useState(onboarding)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.options().then(setOptions).catch((e: ApiError) => setError(e.message))
    if (onboarding) return
    api
      .getProfile()
      .then((p) =>
        setForm({
          age: String(p.age),
          sex: p.sex,
          height_cm: String(p.height_cm),
          weight_kg: String(p.weight_kg),
          activity_level: p.activity_level,
          goal: p.goal,
          allergies: p.allergies,
          diet_type: p.diet_type,
          bmi_standard: p.bmi_standard,
          equipment: p.equipment,
        }),
      )
      .catch((e: ApiError) => setError(e.message))
      .finally(() => setLoaded(true))
  }, [onboarding])

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setSaved(false)
    setForm((f) => ({ ...f, [key]: value }))
  }

  const toggleAllergy = (key: string) =>
    set(
      'allergies',
      form.allergies.includes(key) ? form.allergies.filter((a) => a !== key) : [...form.allergies, key],
    )

  const bmi = bmiFrom(Number(form.height_cm), Number(form.weight_kg))
  const cutoffs = BMI_CUTOFFS[form.bmi_standard]

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    const payload: ProfileInput = {
      ...form,
      age: Number(form.age),
      height_cm: Number(form.height_cm),
      weight_kg: Number(form.weight_kg),
    }
    try {
      await api.saveProfile(payload, today())
      if (onboarding) {
        markProfileComplete()
        navigate('/')
      } else {
        setSaved(true)
      }
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  if (!loaded) return <div className="loading">Loading profile…</div>

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{onboarding ? `Welcome, ${user?.name.split(' ')[0]}!` : 'Your profile'}</h1>
          <p className="muted">
            {onboarding
              ? 'Tell us a bit about yourself so we can build your workout and diet plan.'
              : 'Update your details — your plans recalculate automatically.'}
          </p>
        </div>
      </div>

      <form className="grid grid-2" onSubmit={submit} style={{ alignItems: 'start' }}>
        <div className="stack">
          <section className="card stack">
            <h2>Body measurements</h2>
            <div className="form-grid">
              <label className="field">
                <span>Height (cm)</span>
                <input
                  className="input"
                  type="number"
                  inputMode="decimal"
                  min={100}
                  max={250}
                  step="0.1"
                  value={form.height_cm}
                  onChange={(e) => set('height_cm', e.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span>Weight (kg)</span>
                <input
                  className="input"
                  type="number"
                  inputMode="decimal"
                  min={30}
                  max={300}
                  step="0.1"
                  value={form.weight_kg}
                  onChange={(e) => set('weight_kg', e.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span>Age</span>
                <input
                  className="input"
                  type="number"
                  inputMode="numeric"
                  min={13}
                  max={100}
                  value={form.age}
                  onChange={(e) => set('age', e.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span>Sex</span>
                <select className="input" value={form.sex} onChange={(e) => set('sex', e.target.value as Sex)}>
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                  <option value="other">Other / prefer not to say</option>
                </select>
              </label>
            </div>

            <div className="card inset stack" style={{ gap: 12 }}>
              <div>
                <div className="spread">
                  <span className="stat-label">Body Mass Index (auto-calculated)</span>
                  {bmi !== null && <BmiTag category={bmiCategory(bmi, cutoffs)} />}
                </div>
                <div className="stat-value">{bmi ?? '—'}</div>
                {bmi !== null ? (
                  <BmiScale bmi={bmi} cutoffs={cutoffs} />
                ) : (
                  <p className="small muted">Enter your height and weight to see your BMI.</p>
                )}
              </div>
              <div className="field">
                <span>BMI ranges</span>
                <div className="segmented" role="radiogroup" aria-label="BMI ranges">
                  <label className="chip">
                    <input
                      type="radio"
                      name="bmi_standard"
                      checked={form.bmi_standard === 'who'}
                      onChange={() => set('bmi_standard', 'who')}
                    />
                    International (WHO)
                  </label>
                  <label className="chip">
                    <input
                      type="radio"
                      name="bmi_standard"
                      checked={form.bmi_standard === 'asian'}
                      onChange={() => set('bmi_standard', 'asian')}
                    />
                    Asian
                  </label>
                </div>
                <small className="muted">
                  Asian ranges (overweight from 23, obese from 27.5) are recommended for people of South Asian,
                  East Asian and Southeast Asian descent, who face health risks at a lower BMI.
                </small>
              </div>
            </div>
          </section>

          <section className="card stack">
            <div>
              <h2>Diet type</h2>
              <p className="small muted">Your meal plans will only include foods that match.</p>
            </div>
            <div className="choice-list" role="radiogroup" aria-label="Diet type">
              {options?.diet_types.map((d) => {
                const key = d.key as DietType
                return (
                  <label className="choice" key={key}>
                    <input
                      type="radio"
                      name="diet_type"
                      checked={form.diet_type === key}
                      onChange={() => set('diet_type', key)}
                    />
                    <span>
                      <strong>{d.label.split(' (')[0]}</strong>
                      <span className="small muted">{DIET_HINTS[key]}</span>
                    </span>
                  </label>
                )
              })}
            </div>
          </section>
        </div>

        <div className="stack">
          <section className="card stack">
            <h2>Goal & training</h2>
            <label className="field">
              <span>Goal</span>
              <select className="input" value={form.goal} onChange={(e) => set('goal', e.target.value as Goal)}>
                {Object.entries(GOAL_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Activity level</span>
              <select
                className="input"
                value={form.activity_level}
                onChange={(e) => set('activity_level', e.target.value as ActivityLevel)}
              >
                {Object.entries(ACTIVITY_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Workout equipment</span>
              <select
                className="input"
                value={form.equipment}
                onChange={(e) => set('equipment', e.target.value as Equipment)}
              >
                {options?.equipment.map((o) => (
                  <option key={o.key} value={o.key}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          </section>

          <section className="card stack">
            <div>
              <h2>Food allergies</h2>
              <p className="small muted">Foods containing these will never appear in your meal plan.</p>
            </div>
            <div className="segmented" role="group" aria-label="Allergies">
              {options?.allergens.map((a) => (
                <label className="chip" key={a.key}>
                  <input
                    type="checkbox"
                    checked={form.allergies.includes(a.key)}
                    onChange={() => toggleAllergy(a.key)}
                  />
                  {a.label}
                </label>
              ))}
            </div>
          </section>

          {error && <div className="alert alert-danger">{error}</div>}
          {saved && <div className="alert alert-info">Profile saved. Your plans have been updated.</div>}
          <button className="btn btn-primary" disabled={busy}>
            {busy ? 'Saving…' : onboarding ? 'Build my plan' : 'Save changes'}
          </button>
        </div>
      </form>
    </>
  )
}
