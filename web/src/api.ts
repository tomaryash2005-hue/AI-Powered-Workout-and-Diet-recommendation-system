export type Sex = 'male' | 'female' | 'other'
export type ActivityLevel = 'sedentary' | 'light' | 'moderate' | 'active' | 'very_active'
export type Goal = 'lose' | 'maintain' | 'gain'
export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snack'

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
}

export interface Metrics {
  bmi: number
  bmi_category: 'underweight' | 'normal' | 'overweight' | 'obese'
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

export interface Allergen {
  key: string
  label: string
}

export interface Nutrition {
  calories: number
  protein_g: number
  carbs_g: number
  fat_g: number
}

export interface PlannedItem extends Nutrition {
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
  excluded_allergens: string[]
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

  getProfile: () => request<Profile>('GET', '/api/profile'),
  saveProfile: (p: ProfileInput) => request<Profile>('PUT', '/api/profile', p),

  allergens: () => request<Allergen[]>('GET', '/api/foods/allergens'),
  searchFoods: (q: string, mealType?: MealType) =>
    request<Food[]>('GET', `/api/foods${qs({ q, meal_type: mealType })}`),

  dietPlan: (day: string) => request<DietPlan>('GET', `/api/recommendations/diet${qs({ day })}`),
  workoutPlan: (day: string) =>
    request<WorkoutPlan>('GET', `/api/recommendations/workout${qs({ day })}`),

  logMeal: (meal: MealLogInput) => request<MealLog>('POST', '/api/meals', meal),
  deleteMeal: (id: number) => request<void>('DELETE', `/api/meals/${id}`),
  summary: (day: string) => request<DailySummary>('GET', `/api/meals/summary${qs({ day })}`),
}
