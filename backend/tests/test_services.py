from dataclasses import dataclass, field
from datetime import date, timedelta

import pytest

from app.data.exercises import EXERCISES
from app.data.foods import DIET_TYPES, FOODS, FOODS_BY_ID, fits_diet
from app.services.diet import build_diet_plan, swap_alternatives
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
    diet_type: str = "non_vegetarian"
    bmi_standard: str = "who"
    equipment: str = "none"


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


def test_diet_type_rules() -> None:
    chicken, salmon, eggs, paneer, dal = (
        FOODS_BY_ID[i] for i in ("chicken_breast", "salmon", "boiled_eggs", "paneer", "lentil_dal")
    )
    assert all(fits_diet(f, "non_vegetarian") for f in (chicken, salmon, eggs, paneer, dal))
    assert not fits_diet(chicken, "pescatarian") and fits_diet(salmon, "pescatarian")
    assert fits_diet(eggs, "eggetarian") and not fits_diet(salmon, "eggetarian")
    assert not fits_diet(eggs, "vegetarian") and fits_diet(paneer, "vegetarian")
    assert not fits_diet(paneer, "vegan") and fits_diet(dal, "vegan")


def test_jain_diet_excludes_root_vegetables_onion_and_garlic() -> None:
    assert fits_diet(FOODS_BY_ID["paneer"], "jain")
    assert fits_diet(FOODS_BY_ID["jain_dal"], "jain")
    for food_id in ("potato", "sweet_potato", "chana_masala", "lentil_dal", "boiled_eggs", "tofu_scramble"):
        assert not fits_diet(FOODS_BY_ID[food_id], "jain"), food_id
    # Anything a Jain can eat is also vegetarian.
    assert all(fits_diet(f, "vegetarian") for f in FOODS if fits_diet(f, "jain"))


def test_jain_with_allergies_still_gets_full_plan() -> None:
    profile = P(diet_type="jain", allergies=["dairy", "gluten", "soy", "peanuts"])
    for offset in range(14):
        plan = build_diet_plan(profile, compute_metrics(profile), date(2026, 5, 1) + timedelta(days=offset))
        assert [len(m.items) for m in plan.meals] == [2, 3, 3, 1]


@pytest.mark.parametrize("diet_type", list(DIET_TYPES))
def test_diet_plan_respects_diet_type(diet_type: str) -> None:
    profile = P(diet_type=diet_type)
    for offset in range(14):
        plan = build_diet_plan(profile, compute_metrics(profile), date(2026, 2, 1) + timedelta(days=offset))
        assert [len(m.items) for m in plan.meals] == [2, 3, 3, 1]
        for item in (i for m in plan.meals for i in m.items):
            assert fits_diet(FOODS_BY_ID[item.food_id], diet_type)


def test_vegan_with_many_allergies_still_gets_full_plan() -> None:
    profile = P(diet_type="vegan", allergies=["gluten", "soy", "peanuts", "tree_nuts", "sesame"])
    plan = build_diet_plan(profile, compute_metrics(profile), date(2026, 4, 1))
    assert [len(m.items) for m in plan.meals] == [2, 3, 3, 1]


def test_log_only_foods_are_never_planned() -> None:
    planned = set()
    for offset in range(60):
        plan = build_diet_plan(P(), compute_metrics(P()), date(2026, 1, 1) + timedelta(days=offset))
        planned |= {i.food_id for m in plan.meals for i in m.items}
    assert not any(FOODS_BY_ID[f].category in ("meal", "treat") for f in planned)


def test_food_database_is_consistent() -> None:
    assert len(FOODS) >= 100
    assert len({f.id for f in FOODS}) == len(FOODS)
    for f in FOODS:
        kcal = f.protein_g * 4 + f.carbs_g * 4 + f.fat_g * 9
        assert abs(kcal - f.calories) / f.calories < 0.25, f.name


def test_asian_bmi_cutoffs() -> None:
    who = compute_metrics(P(weight_kg=72))
    asian = compute_metrics(P(weight_kg=72, bmi_standard="asian"))
    assert who.bmi == asian.bmi == 23.5
    assert who.bmi_category == "normal"
    assert asian.bmi_category == "overweight"
    assert asian.healthy_weight_range_kg[1] < who.healthy_weight_range_kg[1]
    assert bmi_category(27.5, "asian") == "obese"


def test_asian_obese_gets_low_impact_workouts() -> None:
    profile = P(weight_kg=86, bmi_standard="asian")  # BMI 28.1
    plan = build_workout_plan(profile, compute_metrics(profile), date(2026, 1, 5))
    assert plan.low_impact


@pytest.mark.parametrize("equipment", ["none", "dumbbells", "gym"])
def test_workout_uses_available_equipment(equipment: str) -> None:
    allowed = {"none": {"none"}, "dumbbells": {"none", "dumbbells"}, "gym": {"none", "dumbbells", "gym"}}
    by_name = {e.name: e for e in EXERCISES}
    profile = P(equipment=equipment, activity_level="active")
    plan = build_workout_plan(profile, compute_metrics(profile), date(2026, 1, 5))
    used = [by_name[e.name] for d in plan.week for e in d.exercises if e.name in by_name]
    assert used and all(e.equipment in allowed[equipment] for e in used)
    if equipment != "none":
        strength = [e for e in used if e.group in ("upper", "lower")]
        assert all(e.equipment == equipment for e in strength)


def test_swaps_replace_dish_and_invalid_swaps_are_ignored() -> None:
    profile = P(diet_type="vegetarian")
    day = date(2026, 6, 1)
    metrics = compute_metrics(profile)
    plan = build_diet_plan(profile, metrics, day)
    alternatives = swap_alternatives(plan, profile, "lunch", 0)
    in_plan = {i.food_id for m in plan.meals for i in m.items}
    assert alternatives and not {a.food_id for a in alternatives} & in_plan
    assert all(fits_diet(FOODS_BY_ID[a.food_id], "vegetarian") for a in alternatives)

    choice = alternatives[0].food_id
    swapped = build_diet_plan(profile, metrics, day, {("lunch", 0): choice, ("dinner", 0): "chicken_breast"})
    lunch = next(m for m in swapped.meals if m.meal_type == "lunch")
    dinner = next(m for m in swapped.meals if m.meal_type == "dinner")
    assert lunch.items[0].food_id == choice and lunch.items[0].swapped
    assert dinner.items[0].food_id != "chicken_breast"
    assert swapped.has_swaps
