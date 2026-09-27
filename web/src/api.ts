export type Sex = 'male' | 'female' | 'other'
export type ActivityLevel = 'sedentary' | 'light' | 'moderate' | 'active' | 'very_active'
export type Goal = 'lose' | 'maintain' | 'gain'
export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snack'
export type DietType = 'non_vegetarian' | 'pescatarian' | 'eggetarian' | 'vegetarian' | 'jain' | 'vegan'
export type BmiStandard = 'who' | 'asian'
export type Equipment = 'none' | 'dumbbells' | 'gym'
export type BmiCategory = 'underweight' | 'normal' | 'overweight' | 'obese'

export interface User {
  id: number
  name: string
  email: string
  has_profile: boolean
}

export interface TokenResponse {
  access_token: string
  user: User
}

export interface ProfileInput {
  age: number
  sex: Sex
  height_cm: number
  weight_kg: number
  activity_level: ActivityLevel
  goal: Goal
  allergies: string[]
  diet_type: DietType
  bmi_standard: BmiStandard
  equipment: Equipment
}

export interface Metrics {
  bmi: number
  bmi_category: BmiCategory
  bmi_standard: BmiStandard
  bmi_cutoffs: [number, number, number]
  bmr: number
  tdee: number
  effective_goal: Goal
  target_calories: number
  protein_g: number
  carbs_g: number
  fat_g: number
  water_liters: number
  healthy_weight_range_kg: [number, number]
  warnings: string[]
}

export interface Profile extends ProfileInput {
  metrics: Metrics
}

export interface Option {
  key: string
  label: string
}

export interface Options {
  allergens: Option[]
  diet_types: Option[]
  equipment: Option[]
  usda_search: boolean
  password_reset: boolean
  push_public_key: string | null
  ai_logging: boolean
}

export interface AiMealItem {
  food_id: string | null
  name: string
  serving: string
  servings: number
  per_serving: Nutrition
  allergens: string[]
  conflicts_with_allergies: string[]
  fits_diet: boolean
  confidence: 'high' | 'medium' | 'low'
}

export interface AiParseResult {
  items: AiMealItem[]
  notes: string
  remaining_today: number
}

export interface AiImage {
  media_type: 'image/jpeg' | 'image/png' | 'image/webp' | 'image/gif'
  data: string
}

export interface Nutrition {
  calories: number
  protein_g: number
  carbs_g: number
  fat_g: number
}

export interface PlannedItem extends Nutrition {
  slot: number
  target_calories: number
  swapped: boolean
  food_id: string
  name: string
  serving: string
  servings: number
}

export interface PlannedMeal {
  meal_type: MealType
  target_calories: number
  calories: number
  items: PlannedItem[]
}

export interface DietPlan extends Nutrition {
  date: string
  target_calories: number
  meals: PlannedMeal[]
  diet_type: DietType
  excluded_allergens: string[]
  has_swaps: boolean
  tips: string[]
}

export interface PlannedExercise {
  name: string
  sets: number
  reps: string
  rest_seconds: number
  tip: string
}

export interface WorkoutDay {
  day: string
  focus: 'full_body' | 'upper' | 'lower' | 'cardio' | 'rest'
  title: string
  duration_min: number
  exercises: PlannedExercise[]
}

export interface WorkoutPlan {
  goal: Goal
  level: string
  low_impact: boolean
  equipment: Equipment
  days_per_week: number
  week: WorkoutDay[]
  notes: string[]
}

export interface Food extends Nutrition {
  id: string
  name: string
  serving: string
  category: string
  meal_types: MealType[]
  allergens: string[]
  conflicts_with_allergies: string[]
  fits_diet: boolean
  source: 'builtin' | 'usda'
}

export interface MealLog extends Nutrition {
  id: number
  date: string
  meal_type: MealType
  food_id: string | null
  name: string
  servings: number
  allergens: string[]
  allergy_warning: string[]
}

export type MealLogInput =
  | { date: string; meal_type: MealType; food_id: string; servings: number }
  | ({ date: string; meal_type: MealType; name: string; allergens: string[] } & Nutrition)

export interface Progress {
  consumed: number
  target: number
  remaining: number
}

export interface DailySummary {
  date: string
  calories: Progress
  protein_g: Progress
  carbs_g: Progress
  fat_g: Progress
  meals: MealLog[]
}

export interface DayTotals extends Nutrition {
  date: string
}

export interface History {
  target_calories: number
  days: DayTotals[]
}

export interface WeightEntry {
  id: number
  date: string
  weight_kg: number
}

export interface WorkoutSet {
  exercise: string
  set_number: number
  reps: number | null
  weight_kg: number | null
  duration_s: number | null
}

export interface WorkoutInput {
  date: string
  title: string
  duration_min: number | null
  notes: string | null
  sets: WorkoutSet[]
}

export interface Workout extends WorkoutInput {
  id: number
}

export interface StrengthSeries {
  exercise: string
  points: { date: string; best_weight_kg: number }[]
}

export interface ReminderSettings {
  timezone: string
  meals_enabled: boolean
  breakfast_time: string
  lunch_time: string
  dinner_time: string
  weigh_in_enabled: boolean
  weigh_in_weekday: number
  weigh_in_time: string
  workout_enabled: boolean
  workout_time: string
}

export interface ReminderSettingsOut extends ReminderSettings {
  push_devices: number
}

const TOKEN_KEY = 'fitai_token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Storage unavailable (private mode); the session just won't persist.
  }
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

let onUnauthorized: () => void = () => {}

export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler
}

function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail[0]?.msg) {
      return String(detail[0].msg).replace(/^Value error, /, '')
    }
  }
  return fallback
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  const res = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized()
    throw new ApiError(res.status, errorMessage(data, `Request failed (${res.status})`))
  }
  return data as T
}

async function download(path: string, filename: string): Promise<void> {
  const token = getToken()
  const res = await fetch(path, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!res.ok) throw new ApiError(res.status, `Download failed (${res.status})`)
  const url = URL.createObjectURL(await res.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

const qs = (params: Record<string, string | undefined>) => {
  const search = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v) search.set(k, v)
  const s = search.toString()
  return s ? `?${s}` : ''
}

export const api = {
  register: (name: string, email: string, password: string) =>
    request<TokenResponse>('POST', '/api/auth/register', { name, email, password }),
  login: (email: string, password: string) =>
    request<TokenResponse>('POST', '/api/auth/login', { email, password }),
  me: () => request<User>('GET', '/api/auth/me'),
  forgotPassword: (email: string) => request<{ detail: string }>('POST', '/api/auth/forgot-password', { email }),
  resetPassword: (token: string, newPassword: string) =>
    request<TokenResponse>('POST', '/api/auth/reset-password', { token, new_password: newPassword }),
  changePassword: (currentPassword: string, newPassword: string) =>
    request<TokenResponse>('POST', '/api/account/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),
  exportData: () => download('/api/account/export', 'fitai-export.json'),
  deleteAccount: (password: string) => request<void>('DELETE', '/api/account', { password }),

  getProfile: () => request<Profile>('GET', '/api/profile'),
  saveProfile: (p: ProfileInput, asOf: string) =>
    request<Profile>('PUT', '/api/profile', { ...p, as_of: asOf }),

  options: () => request<Options>('GET', '/api/foods/options'),
  searchFoods: (q: string, mealType?: MealType) =>
    request<Food[]>('GET', `/api/foods${qs({ q, meal_type: mealType })}`),

  dietPlan: (day: string) => request<DietPlan>('GET', `/api/recommendations/diet${qs({ day })}`),
  alternatives: (day: string, mealType: MealType, slot: number) =>
    request<PlannedItem[]>(
      'GET',
      `/api/recommendations/diet/alternatives${qs({ day, meal_type: mealType, slot: String(slot) })}`,
    ),
  swapDish: (day: string, mealType: MealType, slot: number, foodId: string) =>
    request<DietPlan>('PUT', '/api/recommendations/diet/swap', {
      day,
      meal_type: mealType,
      slot,
      food_id: foodId,
    }),
  resetSwaps: (day: string) => request<DietPlan>('DELETE', `/api/recommendations/diet/swaps${qs({ day })}`),
  workoutPlan: (day: string) =>
    request<WorkoutPlan>('GET', `/api/recommendations/workout${qs({ day })}`),

  logMeal: (meal: MealLogInput) => request<MealLog>('POST', '/api/meals', meal),
  parseMeal: (mealType: MealType, text: string, image: AiImage | null) =>
    request<AiParseResult>('POST', '/api/ai/parse-meal', { meal_type: mealType, text: text || null, image }),
  deleteMeal: (id: number) => request<void>('DELETE', `/api/meals/${id}`),
  summary: (day: string) => request<DailySummary>('GET', `/api/meals/summary${qs({ day })}`),
  history: (end: string, days: number) =>
    request<History>('GET', `/api/meals/history${qs({ end, days: String(days) })}`),

  weights: (end: string, days: number) =>
    request<WeightEntry[]>('GET', `/api/weight${qs({ end, days: String(days) })}`),
  logWeight: (date: string, weightKg: number) =>
    request<WeightEntry>('PUT', '/api/weight', { date, weight_kg: weightKg }),
  deleteWeight: (id: number) => request<void>('DELETE', `/api/weight/${id}`),

  workouts: (end: string, days: number) =>
    request<Workout[]>('GET', `/api/workouts${qs({ end, days: String(days) })}`),
  logWorkout: (workout: WorkoutInput) => request<Workout>('POST', '/api/workouts', workout),
  deleteWorkout: (id: number) => request<void>('DELETE', `/api/workouts/${id}`),
  strength: (end: string, days: number) =>
    request<StrengthSeries[]>('GET', `/api/workouts/strength${qs({ end, days: String(days) })}`),

  reminderSettings: () => request<ReminderSettingsOut>('GET', '/api/notifications/settings'),
  saveReminderSettings: (s: ReminderSettings) =>
    request<ReminderSettingsOut>('PUT', '/api/notifications/settings', s),
  subscribePush: (sub: PushSubscriptionJSON) => request<void>('POST', '/api/notifications/subscriptions', sub),
  unsubscribePush: (endpoint: string) =>
    request<void>('POST', '/api/notifications/subscriptions/remove', { endpoint }),
  testNotification: () => request<{ sent: number }>('POST', '/api/notifications/test'),
}
