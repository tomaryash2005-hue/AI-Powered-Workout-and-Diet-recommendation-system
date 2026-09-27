import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  api,
  ApiError,
  type ActivityLevel,
  type Allergen,
  type Goal,
  type ProfileInput,
  type Sex,
} from '../api'
import { useAuth } from '../useAuth'
import { BmiScale, BmiTag } from '../components/Progress'
import { ACTIVITY_LABELS, bmiFrom, GOAL_LABELS } from '../utils'

interface FormState {
  age: string
  sex: Sex
  height_cm: string
  weight_kg: string
  activity_level: ActivityLevel
  goal: Goal
  allergies: string[]
}

const EMPTY: FormState = {
  age: '',
  sex: 'female',
  height_cm: '',
  weight_kg: '',
  activity_level: 'light',
  goal: 'maintain',
  allergies: [],
}

export default function ProfilePage() {
  const { user, markProfileComplete } = useAuth()
  const navigate = useNavigate()
  const onboarding = !user?.has_profile
  const [form, setForm] = useState<FormState>(EMPTY)
  const [allergens, setAllergens] = useState<Allergen[]>([])
  const [loaded, setLoaded] = useState(onboarding)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.allergens().then(setAllergens).catch(() => setAllergens([]))
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
      await api.saveProfile(payload)
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

            <div className="card" style={{ background: 'var(--surface-2)', boxShadow: 'none' }}>
              <div className="spread">
                <span className="stat-label">Body Mass Index (auto-calculated)</span>
                {bmi !== null && <BmiTag bmi={bmi} />}
              </div>
              <div className="stat-value">{bmi ?? '—'}</div>
              {bmi !== null ? (
                <BmiScale bmi={bmi} />
              ) : (
                <p className="small muted">Enter your height and weight to see your BMI.</p>
              )}
            </div>
          </section>
        </div>

        <div className="stack">
          <section className="card stack">
            <h2>Goal & activity</h2>
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
          </section>

          <section className="card stack">
            <div>
              <h2>Food allergies</h2>
              <p className="small muted">Foods containing these will never appear in your meal plan.</p>
            </div>
            <div className="segmented" role="group" aria-label="Allergies">
              {allergens.map((a) => (
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
