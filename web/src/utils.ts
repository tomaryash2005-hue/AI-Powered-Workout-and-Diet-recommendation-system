import { useEffect, useState } from 'react'
import type { ActivityLevel, BmiCategory, BmiStandard, Equipment, Goal, MealType } from './api'

export function toISODate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export const today = () => toISODate(new Date())

export const dayMs = (iso: string) => {
  const [y, m, d] = iso.split('-').map(Number)
  return Date.UTC(y, m - 1, d)
}

export const shortDate = (iso: string) =>
  new Date(dayMs(iso)).toLocaleDateString(undefined, { month: 'short', day: 'numeric', timeZone: 'UTC' })

export function shiftDate(iso: string, days: number): string {
  const [y, m, d] = iso.split('-').map(Number)
  return toISODate(new Date(y, m - 1, d + days))
}

export function formatDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  if (iso === today()) return 'Today'
  if (iso === shiftDate(today(), -1)) return 'Yesterday'
  if (iso === shiftDate(today(), 1)) return 'Tomorrow'
  return new Date(y, m - 1, d).toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

export const todayWeekday = () => new Date().toLocaleDateString('en-US', { weekday: 'long' })

export const MEAL_LABELS: Record<MealType, string> = {
  breakfast: 'Breakfast',
  lunch: 'Lunch',
  dinner: 'Dinner',
  snack: 'Snack',
}

export const MEAL_TYPES = Object.keys(MEAL_LABELS) as MealType[]

export const GOAL_LABELS: Record<Goal, string> = {
  lose: 'Lose weight',
  maintain: 'Maintain weight',
  gain: 'Build muscle / gain weight',
}

export const EQUIPMENT_LABELS: Record<Equipment, string> = {
  none: 'bodyweight',
  dumbbells: 'dumbbells',
  gym: 'full gym',
}

export const ACTIVITY_LABELS: Record<ActivityLevel, string> = {
  sedentary: 'Sedentary (little or no exercise)',
  light: 'Lightly active (1–3 days/week)',
  moderate: 'Moderately active (3–5 days/week)',
  active: 'Very active (6–7 days/week)',
  very_active: 'Extremely active (physical job + training)',
}

export function defaultMealType(): MealType {
  const h = new Date().getHours()
  if (h < 11) return 'breakfast'
  if (h < 15) return 'lunch'
  if (h < 18) return 'snack'
  return 'dinner'
}

export function bmiFrom(heightCm: number, weightKg: number): number | null {
  if (!(heightCm > 0) || !(weightKg > 0)) return null
  return Math.round((weightKg / (heightCm / 100) ** 2) * 10) / 10
}

export const BMI_CUTOFFS: Record<BmiStandard, [number, number, number]> = {
  who: [18.5, 25, 30],
  asian: [18.5, 23, 27.5],
}

export function bmiCategory(bmi: number, [normal, overweight, obese]: [number, number, number]): BmiCategory {
  if (bmi < normal) return 'underweight'
  if (bmi < overweight) return 'normal'
  if (bmi < obese) return 'overweight'
  return 'obese'
}

export const fmt = (n: number) => Math.round(n).toLocaleString()

interface AsyncResult<T> {
  load: () => Promise<T>
  data: T | null
  error: string | null
}

// Results are tagged with the loader that produced them, so a new loader (e.g. a different date)
// shows no stale data unless keepPrevious is set; reload() keeps the current data visible until
// fresh data arrives.
export function useAsync<T>(load: () => Promise<T>, { keepPrevious = false } = {}) {
  const [result, setResult] = useState<AsyncResult<T> | null>(null)
  const [version, setVersion] = useState(0)

  useEffect(() => {
    let cancelled = false
    load()
      .then((data) => !cancelled && setResult({ load, data, error: null }))
      .catch((e: Error) => !cancelled && setResult({ load, data: null, error: e.message }))
    return () => {
      cancelled = true
    }
  }, [load, version])

  const current = result?.load === load ? result : null
  return {
    data: current?.data ?? (keepPrevious ? (result?.data ?? null) : null),
    loading: current === null,
    error: current?.error ?? null,
    reload: () => setVersion((v) => v + 1),
  }
}
