from dataclasses import dataclass, field
from datetime import date, timedelta

import pytest

from app.data.foods import FOODS_BY_ID
from app.services.diet import build_diet_plan
from app.services.health import bmi_category, calculate_bmi, compute_metrics
from app.services.workout import build_workout_plan


@dataclass
class P:
    age: int = 30
    sex: str = "male"
    height_cm: float = 175
    weight_kg: float = 70
    activity_level: str = "moderate"
    goal: str = "maintain"
    allergies: list[str] = field(default_factory=list)


@pytest.mark.parametrize(
    "bmi, category",
    [(18.4, "underweight"), (18.5, "normal"), (24.9, "normal"), (25, "overweight"), (30, "obese")],
)
def test_bmi_category_boundaries(bmi: float, category: str) -> None:
    assert bmi_category(bmi) == category


def test_bmi_calculation() -> None:
    assert calculate_bmi(175, 70) == 22.9


def test_metrics_mifflin_st_jeor() -> None:
    m = compute_metrics(P())
    # 10*70 + 6.25*175 - 5*30 + 5 = 1648.75; * 1.55
    assert m.bmr == 1649
    assert m.tdee == round(1648.75 * 1.55)
    assert m.target_calories == m.tdee


def test_lose_goal_applies_deficit_and_gain_applies_surplus() -> None:
    base = compute_metrics(P()).tdee
    assert compute_metrics(P(goal="lose")).target_calories == base - 500
    assert compute_metrics(P(goal="gain")).target_calories == base + 300


def test_underweight_user_cannot_target_weight_loss() -> None:
    m = compute_metrics(P(weight_kg=50, goal="lose"))
    assert m.bmi_category == "underweight"
    assert m.effective_goal == "maintain"
    assert m.warnings


def test_calorie_floor() -> None:
    m = compute_metrics(P(sex="female", age=80, height_cm=150, weight_kg=45, activity_level="sedentary", goal="lose"))
    assert m.target_calories >= 1200


def test_macros_add_up_to_target() -> None:
    m = compute_metrics(P(goal="lose"))
    kcal = m.protein_g * 4 + m.carbs_g * 4 + m.fat_g * 9
    assert abs(kcal - m.target_calories) < 15


@pytest.mark.parametrize("allergies", [[], ["gluten"], ["dairy", "eggs", "peanuts"], ["fish", "shellfish", "soy", "tree_nuts", "sesame"]])
def test_diet_plan_excludes_allergens(allergies: list[str]) -> None:
    profile = P(allergies=allergies)
    for offset in range(14):
        plan = build_diet_plan(profile, compute_metrics(profile), date(2026, 1, 1) + timedelta(days=offset))
        for meal in plan.meals:
            assert meal.items
            for item in meal.items:
                assert not set(FOODS_BY_ID[item.food_id].allergens) & set(allergies)


def test_diet_plan_is_close_to_target() -> None:
    for goal in ("lose", "maintain", "gain"):
        profile = P(goal=goal)
        metrics = compute_metrics(profile)
        plan = build_diet_plan(profile, metrics, date(2026, 3, 10))
        assert abs(plan.calories - metrics.target_calories) / metrics.target_calories < 0.15


def test_diet_plan_does_not_repeat_foods_within_a_day() -> None:
    plan = build_diet_plan(P(), compute_metrics(P()), date(2026, 5, 5))
    ids = [i.food_id for m in plan.meals for i in m.items]
    assert len(ids) == len(set(ids))


def test_workout_plan_structure() -> None:
    plan = build_workout_plan(P(), compute_metrics(P()), date(2026, 1, 5))
    assert len(plan.week) == 7
    training = [d for d in plan.week if d.focus != "rest"]
    assert len(training) == plan.days_per_week == 4


def test_high_bmi_gets_low_impact_plan() -> None:
    profile = P(weight_kg=110, goal="lose")
    plan = build_workout_plan(profile, compute_metrics(profile), date(2026, 1, 5))
    assert plan.low_impact
    names = {e.name for d in plan.week for e in d.exercises}
    assert not names & {"Jump squats", "Jogging", "Mountain climbers"}
    assert not any("HIIT" in n for n in names)


def test_beginner_volume() -> None:
    profile = P(activity_level="sedentary", goal="gain")
    plan = build_workout_plan(profile, compute_metrics(profile), date(2026, 1, 5))
    assert plan.level == "beginner"
    strength = [e for d in plan.week if d.focus in ("full_body", "upper", "lower") for e in d.exercises]
    assert strength and all(e.sets == 3 for e in strength)
