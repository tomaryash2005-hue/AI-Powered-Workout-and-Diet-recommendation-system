from dataclasses import dataclass, field
from typing import Protocol


class BodyProfile(Protocol):
    age: int
    sex: str
    height_cm: float
    weight_kg: float
    activity_level: str
    goal: str
    allergies: list[str]


ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

MIN_CALORIES = {"male": 1500, "female": 1200, "other": 1350}
SEX_CONSTANT = {"male": 5, "female": -161, "other": -78}
PROTEIN_PER_KG = {"lose": 1.8, "maintain": 1.4, "gain": 1.8}


@dataclass
class HealthMetrics:
    bmi: float
    bmi_category: str
    bmr: int
    tdee: int
    effective_goal: str
    target_calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    water_liters: float
    healthy_weight_range_kg: tuple[float, float]
    warnings: list[str] = field(default_factory=list)


def calculate_bmi(height_cm: float, weight_kg: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m**2), 1)


def bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "underweight"
    if bmi < 25:
        return "normal"
    if bmi < 30:
        return "overweight"
    return "obese"


def calculate_bmr(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    """Mifflin-St Jeor equation."""
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + SEX_CONSTANT[sex]


def compute_metrics(p: BodyProfile) -> HealthMetrics:
    warnings: list[str] = []
    bmi = calculate_bmi(p.height_cm, p.weight_kg)
    category = bmi_category(bmi)
    bmr = calculate_bmr(p.sex, p.weight_kg, p.height_cm, p.age)
    tdee = bmr * ACTIVITY_FACTORS[p.activity_level]

    goal = p.goal
    if goal == "lose" and category == "underweight":
        goal = "maintain"
        warnings.append(
            "Your BMI is in the underweight range, so weight loss isn't recommended. "
            "Your plan targets maintenance instead."
        )

    if goal == "lose":
        target = tdee - min(500, 0.2 * tdee)
    elif goal == "gain":
        target = tdee + 300
    else:
        target = tdee

    floor = MIN_CALORIES[p.sex]
    if target < floor:
        target = floor
        warnings.append(
            f"Your calorie target was raised to the safe minimum of {floor} kcal/day."
        )

    height_m = p.height_cm / 100
    # Protein scales with a reference weight at BMI 25 for higher BMIs, to avoid overshooting.
    protein_weight = min(p.weight_kg, 25 * height_m**2)
    protein_g = PROTEIN_PER_KG[goal] * protein_weight
    fat_g = target * 0.25 / 9
    carbs_g = max(0.0, (target - protein_g * 4 - fat_g * 9) / 4)

    if bmi < 16 or bmi >= 35:
        warnings.append(
            "Your BMI is in a range where we strongly recommend talking to a doctor "
            "or registered dietitian before starting a new diet or exercise plan."
        )
    if p.age < 18:
        warnings.append(
            "These recommendations are designed for adults. Teens should follow "
            "guidance from a doctor or parent/guardian."
        )

    return HealthMetrics(
        bmi=bmi,
        bmi_category=category,
        bmr=round(bmr),
        tdee=round(tdee),
        effective_goal=goal,
        target_calories=round(target),
        protein_g=round(protein_g),
        carbs_g=round(carbs_g),
        fat_g=round(fat_g),
        water_liters=round(p.weight_kg * 0.035, 1),
        healthy_weight_range_kg=(round(18.5 * height_m**2, 1), round(24.9 * height_m**2, 1)),
        warnings=warnings,
    )
