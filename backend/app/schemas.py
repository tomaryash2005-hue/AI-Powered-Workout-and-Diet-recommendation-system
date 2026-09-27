from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.data.foods import ALLERGENS

Sex = Literal["male", "female", "other"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]
Goal = Literal["lose", "maintain", "gain"]
MealType = Literal["breakfast", "lunch", "dinner", "snack"]


# --- Auth ---

class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, v: str) -> str:
        if len(v.encode()) > 72:
            raise ValueError("Password must be at most 72 bytes")
        return v


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

    @field_validator("allergies")
    @classmethod
    def known_allergens(cls, v: list[str]) -> list[str]:
        unknown = set(v) - ALLERGENS.keys()
        if unknown:
            raise ValueError(f"Unknown allergens: {', '.join(sorted(unknown))}")
        return sorted(set(v))


class MetricsOut(BaseModel):
    bmi: float
    bmi_category: str
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
    food_id: str
    name: str
    serving: str
    servings: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


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
    excluded_allergens: list[str]
    tips: list[str]


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


class AllergenOut(BaseModel):
    key: str
    label: str


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
