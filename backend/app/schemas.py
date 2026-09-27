from datetime import date as Date
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.data.foods import ALLERGENS

Sex = Literal["male", "female", "other"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]
Goal = Literal["lose", "maintain", "gain"]
MealType = Literal["breakfast", "lunch", "dinner", "snack"]
DietType = Literal["non_vegetarian", "pescatarian", "eggetarian", "vegetarian", "jain", "vegan"]
BmiStandard = Literal["who", "asian"]
Equipment = Literal["none", "dumbbells", "gym"]


# --- Auth ---

def _fits_bcrypt(v: str) -> str:
    if len(v.encode()) > 72:
        raise ValueError("Password must be at most 72 bytes")
    return v


NewPassword = Annotated[str, Field(min_length=8), AfterValidator(_fits_bcrypt)]


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: NewPassword


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    has_profile: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Profile & metrics ---

class ProfileIn(BaseModel):
    age: int = Field(ge=13, le=100)
    sex: Sex
    height_cm: float = Field(ge=100, le=250)
    weight_kg: float = Field(ge=30, le=300)
    activity_level: ActivityLevel
    goal: Goal
    allergies: list[str] = []
    diet_type: DietType = "non_vegetarian"
    bmi_standard: BmiStandard = "who"
    equipment: Equipment = "none"

    @field_validator("allergies")
    @classmethod
    def known_allergens(cls, v: list[str]) -> list[str]:
        unknown = set(v) - ALLERGENS.keys()
        if unknown:
            raise ValueError(f"Unknown allergens: {', '.join(sorted(unknown))}")
        return sorted(set(v))


class ProfileSaveIn(ProfileIn):
    # The user's local date, used to record the weigh-in when weight changes.
    as_of: Date | None = None


class MetricsOut(BaseModel):
    bmi: float
    bmi_category: str
    bmi_standard: BmiStandard
    bmi_cutoffs: tuple[float, float, float]
    bmr: int
    tdee: int
    effective_goal: Goal
    target_calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    water_liters: float
    healthy_weight_range_kg: tuple[float, float]
    warnings: list[str]


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)

    metrics: MetricsOut


# --- Recommendations ---

class PlannedItemOut(BaseModel):
    slot: int
    food_id: str
    name: str
    serving: str
    servings: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    target_calories: int
    swapped: bool


class PlannedMealOut(BaseModel):
    meal_type: MealType
    target_calories: int
    calories: float
    items: list[PlannedItemOut]


class DietPlanOut(BaseModel):
    date: Date
    target_calories: int
    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    meals: list[PlannedMealOut]
    diet_type: DietType
    excluded_allergens: list[str]
    has_swaps: bool
    tips: list[str]


class SwapIn(BaseModel):
    day: Date
    meal_type: MealType
    slot: int = Field(ge=0, le=5)
    food_id: str


class PlannedExerciseOut(BaseModel):
    name: str
    sets: int
    reps: str
    rest_seconds: int
    tip: str


class WorkoutDayOut(BaseModel):
    day: str
    focus: str
    title: str
    duration_min: int
    exercises: list[PlannedExerciseOut]


class WorkoutPlanOut(BaseModel):
    goal: Goal
    level: str
    low_impact: bool
    equipment: Equipment
    days_per_week: int
    week: list[WorkoutDayOut]
    notes: list[str]


# --- Foods ---

class FoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    serving: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    category: str
    meal_types: list[str]
    allergens: list[str]
    conflicts_with_allergies: list[str] = []
    fits_diet: bool = True
    source: Literal["builtin", "usda"] = "builtin"


class OptionOut(BaseModel):
    key: str
    label: str


class OptionsOut(BaseModel):
    allergens: list[OptionOut]
    diet_types: list[OptionOut]
    equipment: list[OptionOut]
    usda_search: bool
    password_reset: bool
    push_public_key: str | None


# --- Meal tracking ---

class MealLogIn(BaseModel):
    date: Date
    meal_type: MealType
    servings: float = Field(default=1, gt=0, le=20)
    food_id: str | None = None
    name: str | None = Field(default=None, max_length=120)
    calories: float | None = Field(default=None, ge=0, le=5000)
    protein_g: float = Field(default=0, ge=0, le=500)
    carbs_g: float = Field(default=0, ge=0, le=1000)
    fat_g: float = Field(default=0, ge=0, le=500)
    allergens: list[str] = []

    @model_validator(mode="after")
    def food_or_custom(self) -> "MealLogIn":
        if self.food_id is None and (not self.name or self.calories is None):
            raise ValueError("Provide either food_id or a custom name and calories")
        unknown = set(self.allergens) - ALLERGENS.keys()
        if unknown:
            raise ValueError(f"Unknown allergens: {', '.join(sorted(unknown))}")
        return self


class MealLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: Date
    meal_type: MealType
    food_id: str | None
    name: str
    servings: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    allergens: list[str]
    allergy_warning: list[str] = []


class NutrientProgress(BaseModel):
    consumed: float
    target: float
    remaining: float


class DailySummaryOut(BaseModel):
    date: Date
    calories: NutrientProgress
    protein_g: NutrientProgress
    carbs_g: NutrientProgress
    fat_g: NutrientProgress
    meals: list[MealLogOut]


class DayTotalsOut(BaseModel):
    date: Date
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class HistoryOut(BaseModel):
    target_calories: int
    days: list[DayTotalsOut]


# --- Weight tracking ---

class WeightIn(BaseModel):
    date: Date
    weight_kg: float = Field(ge=30, le=300)


class WeightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: Date
    weight_kg: float


# --- Account ---

class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: NewPassword


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: NewPassword


class DeleteAccountIn(BaseModel):
    password: str


# --- Workout logging ---

class WorkoutSetIn(BaseModel):
    exercise: str = Field(min_length=1, max_length=120)
    set_number: int = Field(ge=1, le=50)
    reps: int | None = Field(default=None, ge=0, le=1000)
    weight_kg: float | None = Field(default=None, ge=0, le=1000)
    duration_s: int | None = Field(default=None, ge=0, le=6 * 3600)


class WorkoutSetOut(WorkoutSetIn):
    model_config = ConfigDict(from_attributes=True)


class WorkoutIn(BaseModel):
    date: Date
    title: str = Field(min_length=1, max_length=100)
    duration_min: int | None = Field(default=None, ge=0, le=600)
    notes: str | None = Field(default=None, max_length=500)
    sets: list[WorkoutSetIn] = Field(default=[], max_length=200)


class WorkoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: Date
    title: str
    duration_min: int | None
    notes: str | None
    sets: list[WorkoutSetOut]


class StrengthPoint(BaseModel):
    date: Date
    best_weight_kg: float


class StrengthSeries(BaseModel):
    exercise: str
    points: list[StrengthPoint]


# --- Reminders & push ---

def _valid_timezone(v: str) -> str:
    try:
        ZoneInfo(v)
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise ValueError(f"Unknown timezone: {v}") from e
    return v


TimeOfDay = Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]


class ReminderSettingsIn(BaseModel):
    timezone: Annotated[str, Field(max_length=64), AfterValidator(_valid_timezone)] = "UTC"
    meals_enabled: bool = False
    breakfast_time: TimeOfDay = "08:30"
    lunch_time: TimeOfDay = "13:00"
    dinner_time: TimeOfDay = "20:00"
    weigh_in_enabled: bool = False
    weigh_in_weekday: int = Field(default=0, ge=0, le=6)
    weigh_in_time: TimeOfDay = "07:30"
    workout_enabled: bool = False
    workout_time: TimeOfDay = "18:00"


class ReminderSettingsOut(ReminderSettingsIn):
    model_config = ConfigDict(from_attributes=True)

    push_devices: int = 0


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=200)
    auth: str = Field(min_length=1, max_length=100)


class PushSubscriptionIn(BaseModel):
    endpoint: str = Field(pattern=r"^https://", max_length=1000)
    keys: PushKeys


class PushUnsubscribeIn(BaseModel):
    endpoint: str = Field(max_length=1000)


class ReminderRunOut(BaseModel):
    users_checked: int
    sent: int
    skipped: int
    removed_subscriptions: int
