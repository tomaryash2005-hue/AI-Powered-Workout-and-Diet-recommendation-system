import { useRef, useState, type ChangeEvent } from 'react'
import { api, type AiImage, type AiMealItem, type MealLog, type MealType } from '../api'
import { prepareImage } from '../image'
import { fmt, MEAL_LABELS } from '../utils'
import { AlertIcon, CameraIcon, TrashIcon } from './Icons'

interface Props {
  day: string
  mealType: MealType
  onAdded: (m: MealLog) => void
}

const CONFIDENCE_HINT = {
  high: null,
  medium: 'Amount estimated',
  low: 'Check this item',
} as const

export default function AiMealLogger({ day, mealType, onAdded }: Props) {
  const [text, setText] = useState('')
  const [photo, setPhoto] = useState<{ image: AiImage; previewUrl: string } | null>(null)
  const [items, setItems] = useState<AiMealItem[] | null>(null)
  const [notes, setNotes] = useState('')
  const [remaining, setRemaining] = useState<number | null>(null)
  const [status, setStatus] = useState<'idle' | 'analysing' | 'logging'>('idle')
  const [error, setError] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  const pickPhoto = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setError(null)
    try {
      setPhoto(await prepareImage(file))
    } catch {
      setError("That photo couldn't be opened. Try a JPEG or PNG.")
    }
  }

  const analyse = async () => {
    setStatus('analysing')
    setError(null)
    try {
      const result = await api.parseMeal(mealType, text.trim(), photo?.image ?? null)
      setItems(result.items)
      setNotes(result.notes)
      setRemaining(result.remaining_today)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setStatus('idle')
    }
  }

  const setServings = (index: number, value: string) =>
    setItems((list) => list!.map((it, i) => (i === index ? { ...it, servings: Number(value) } : it)))

  const remove = (index: number) => setItems((list) => list!.filter((_, i) => i !== index))

  const reset = () => {
    setItems(null)
    setNotes('')
    setText('')
    setPhoto(null)
  }

  const logAll = async () => {
    if (!items) return
    setStatus('logging')
    setError(null)
    try {
      for (const it of items) {
        const logged = it.food_id
          ? await api.logMeal({ date: day, meal_type: mealType, food_id: it.food_id, servings: it.servings })
          : await api.logMeal({
              date: day,
              meal_type: mealType,
              name: it.name,
              calories: it.per_serving.calories * it.servings,
              protein_g: it.per_serving.protein_g * it.servings,
              carbs_g: it.per_serving.carbs_g * it.servings,
              fat_g: it.per_serving.fat_g * it.servings,
              allergens: it.allergens,
            })
        onAdded(logged)
      }
      reset()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setStatus('idle')
    }
  }

  const valid = items?.every((it) => it.servings > 0 && it.servings <= 20) ?? false
  const total = items?.reduce((sum, it) => sum + it.per_serving.calories * (it.servings || 0), 0) ?? 0

  if (items !== null) {
    return (
      <div className="stack" style={{ gap: 10 }}>
        {notes && (
          <div className="alert alert-info">
            <AlertIcon />
            <span>{notes}</span>
          </div>
        )}
        {items.length === 0 ? (
          <p className="small muted">No foods found. Try describing the meal in more detail.</p>
        ) : (
          <ul className="list ai-items">
            {items.map((it, i) => {
              const hint = CONFIDENCE_HINT[it.confidence]
              return (
                <li key={`${it.name}-${i}`}>
                  <div className="list-main">
                    <strong>{it.name}</strong>
                    <div className="small muted">
                      {it.serving}
                      {!it.food_id && ' · AI estimate'}
                    </div>
                    <div className="row" style={{ gap: 4, marginTop: 4 }}>
                      {hint && <span className="tag tag-warn">{hint}</span>}
                      {it.conflicts_with_allergies.length > 0 && (
                        <span className="tag tag-danger">Contains {it.conflicts_with_allergies.join(', ')}</span>
                      )}
                      {!it.fits_diet && <span className="tag tag-warn">Not in your diet</span>}
                    </div>
                  </div>
                  <label className="field ai-servings">
                    <span className="small muted">Servings</span>
                    <input
                      className="input"
                      type="number"
                      inputMode="decimal"
                      min={0.25}
                      max={20}
                      step={0.25}
                      value={Number.isNaN(it.servings) ? '' : it.servings}
                      onChange={(e) => setServings(i, e.target.value)}
                      aria-label={`${it.name} servings`}
                    />
                  </label>
                  <span className="list-end small">{fmt(it.per_serving.calories * (it.servings || 0))} kcal</span>
                  <button
                    type="button"
                    className="btn btn-ghost btn-icon"
                    onClick={() => remove(i)}
                    aria-label={`Remove ${it.name}`}
                  >
                    <TrashIcon />
                  </button>
                </li>
              )
            })}
          </ul>
        )}
        {error && <div className="alert alert-danger">{error}</div>}
        <div className="spread" style={{ flexWrap: 'wrap' }}>
          <span className="small muted num">
            Total {fmt(total)} kcal{remaining !== null && ` · ${remaining} AI requests left today`}
          </span>
          <div className="row">
            <button type="button" className="btn btn-ghost" onClick={() => setItems(null)} disabled={status !== 'idle'}>
              Back
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={logAll}
              disabled={status !== 'idle' || items.length === 0 || !valid}
            >
              {status === 'logging'
                ? 'Logging…'
                : `Log ${items.length} item${items.length === 1 ? '' : 's'} to ${MEAL_LABELS[mealType].toLowerCase()}`}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="stack" style={{ gap: 10 }}>
      <label className="field">
        <span>What did you eat?</span>
        <textarea
          className="input"
          rows={3}
          maxLength={1000}
          placeholder="e.g. 2 rotis, a bowl of dal, some bhindi and a glass of buttermilk"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </label>
      <input ref={fileInput} type="file" accept="image/*" hidden onChange={pickPhoto} />
      {photo ? (
        <div className="row" style={{ alignItems: 'center' }}>
          <img src={photo.previewUrl} alt="Meal photo" className="ai-photo" />
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setPhoto(null)}>
            Remove photo
          </button>
        </div>
      ) : (
        <button type="button" className="btn btn-sm" style={{ alignSelf: 'flex-start' }} onClick={() => fileInput.current?.click()}>
          <CameraIcon /> Add a photo
        </button>
      )}
      <p className="small muted">
        Your description and photo are sent to Claude (Anthropic's AI) to identify the food. Photos aren't stored.
        You can check and edit everything before it's logged.
      </p>
      {error && <div className="alert alert-danger">{error}</div>}
      <button
        type="button"
        className="btn btn-primary"
        onClick={analyse}
        disabled={status !== 'idle' || (!text.trim() && !photo)}
      >
        {status === 'analysing' ? 'Analysing your meal…' : 'Analyse meal'}
      </button>
    </div>
  )
}
