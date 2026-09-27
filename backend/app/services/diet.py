from dataclasses import dataclass, field
from datetime import date

from app.data.foods import FOODS, Food
from app.services.health import BodyProfile, HealthMetrics

MEAL_SPLIT = {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.30, "snack": 0.10}

# Each meal is built from roles: (allowed food categories, share of the meal's calories).
MEAL_ROLES: dict[str, list[tuple[tuple[str, ...], float]]] = {
    "breakfast": [(("protein", "mixed"), 0.65), (("fruit", "dairy", "carb"), 0.35)],
    "lunch": [(("protein",), 0.45), (("carb",), 0.40), (("vegetable",), 0.15)],
    "dinner": [(("protein",), 0.45), (("carb",), 0.40), (("vegetable",), 0.15)],
    "snack": [(("fruit", "snack", "dairy", "protein", "mixed"), 1.0)],
}

MAX_SERVINGS = {"vegetable": 2.0, "fruit": 2.0}

GOAL_TIPS = {
    "lose": [
        "Fill half your plate with vegetables to stay full on fewer calories.",
        "Prioritise protein at every meal to preserve muscle while losing fat.",
        "Limit sugary drinks and fried snacks — they add calories quickly.",
    ],
    "maintain": [
        "Keep meal timing consistent to manage hunger through the day.",
        "Aim for a variety of colourful vegetables and fruit each week.",
    ],
    "gain": [
        "Add an extra snack if you struggle to hit your calorie target.",
        "Eat protein within a couple of hours after strength training.",
        "Calorie-dense foods like nuts, dairy and whole grains make surplus easier.",
    ],
}


@dataclass
class PlannedItem:
    food_id: str
    name: str
    serving: str
    servings: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


@dataclass
class PlannedMeal:
    meal_type: str
    target_calories: int
    items: list[PlannedItem] = field(default_factory=list)
    calories: float = 0


@dataclass
class DietPlan:
    date: date
    target_calories: int
    meals: list[PlannedMeal]
    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    excluded_allergens: list[str]
    tips: list[str]


def safe_foods(allergies: list[str]) -> list[Food]:
    blocked = set(allergies)
    return [f for f in FOODS if not blocked.intersection(f.allergens)]


def _round_servings(raw: float, category: str) -> float:
    servings = round(raw * 2) / 2
    return min(max(servings, 0.5), MAX_SERVINGS.get(category, 3.0))


def _pick(candidates: list[Food], index: int, used: set[str]) -> Food:
    n = len(candidates)
    for offset in range(n):
        food = candidates[(index + offset) % n]
        if food.id not in used:
            return food
    return candidates[index % n]


def build_diet_plan(profile: BodyProfile, metrics: HealthMetrics, day: date) -> DietPlan:
    foods = safe_foods(profile.allergies)
    seed = day.toordinal()
    used: set[str] = set()
    meals: list[PlannedMeal] = []

    for slot_index, (meal_type, share) in enumerate(MEAL_SPLIT.items()):
        meal_kcal = metrics.target_calories * share
        meal = PlannedMeal(meal_type=meal_type, target_calories=round(meal_kcal))

        roles = []
        for categories, weight in MEAL_ROLES[meal_type]:
            candidates = [f for f in foods if f.category in categories and meal_type in f.meal_types]
            if candidates:
                roles.append((candidates, weight))
        total_weight = sum(w for _, w in roles)

        for role_index, (candidates, weight) in enumerate(roles):
            food = _pick(candidates, seed + slot_index * 7 + role_index * 3, used)
            used.add(food.id)
            role_kcal = meal_kcal * weight / total_weight
            servings = _round_servings(role_kcal / food.calories, food.category)
            meal.items.append(
                PlannedItem(
                    food_id=food.id,
                    name=food.name,
                    serving=food.serving,
                    servings=servings,
                    calories=round(food.calories * servings),
                    protein_g=round(food.protein_g * servings, 1),
                    carbs_g=round(food.carbs_g * servings, 1),
                    fat_g=round(food.fat_g * servings, 1),
                )
            )
        meal.calories = round(sum(i.calories for i in meal.items))
        meals.append(meal)

    items = [i for m in meals for i in m.items]
    return DietPlan(
        date=day,
        target_calories=metrics.target_calories,
        meals=meals,
        calories=round(sum(i.calories for i in items)),
        protein_g=round(sum(i.protein_g for i in items)),
        carbs_g=round(sum(i.carbs_g for i in items)),
        fat_g=round(sum(i.fat_g for i in items)),
        excluded_allergens=sorted(profile.allergies),
        tips=GOAL_TIPS[metrics.effective_goal]
        + [f"Drink about {metrics.water_liters} L of water per day."],
    )
