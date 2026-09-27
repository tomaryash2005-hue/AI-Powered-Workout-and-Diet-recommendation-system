from dataclasses import dataclass, field
from datetime import date

from app.data.foods import FOODS, FOODS_BY_ID, LOG_ONLY_CATEGORIES, Food, fits_diet
from app.services.health import BodyProfile, HealthMetrics

MEAL_SPLIT = {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.30, "snack": 0.10}

# Each meal is built from slots: (allowed food categories, share of the meal's calories).
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

DIET_TIPS = {
    "vegan": "Combine legumes with grains (dal + rice, beans + tortillas) for complete protein, "
    "and consider a vitamin B12 supplement.",
    "vegetarian": "Dairy, dal, chickpeas and soy are your best protein sources — include one at every meal.",
    "eggetarian": "Eggs are a cheap, complete protein — they make a great breakfast anchor.",
    "pescatarian": "Aim for oily fish like salmon twice a week for omega-3 fats.",
}

Swaps = dict[tuple[str, int], str]


@dataclass
class PlannedItem:
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
    swapped: bool = False


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
    diet_type: str
    excluded_allergens: list[str]
    has_swaps: bool
    tips: list[str]


def eligible_foods(profile: BodyProfile) -> list[Food]:
    blocked = set(profile.allergies)
    return [
        f
        for f in FOODS
        if f.category not in LOG_ONLY_CATEGORIES
        and not blocked.intersection(f.allergens)
        and fits_diet(f, profile.diet_type)
    ]


def slot_candidates(foods: list[Food], meal_type: str, slot: int) -> list[Food]:
    categories, _ = MEAL_ROLES[meal_type][slot]
    return [f for f in foods if f.category in categories and meal_type in f.meal_types]


def _round_servings(raw: float, category: str) -> float:
    servings = round(raw * 2) / 2
    return min(max(servings, 0.5), MAX_SERVINGS.get(category, 3.0))


def planned_item(food: Food, slot: int, target_kcal: float, swapped: bool = False) -> PlannedItem:
    servings = _round_servings(target_kcal / food.calories, food.category)
    return PlannedItem(
        slot=slot,
        food_id=food.id,
        name=food.name,
        serving=food.serving,
        servings=servings,
        calories=round(food.calories * servings),
        protein_g=round(food.protein_g * servings, 1),
        carbs_g=round(food.carbs_g * servings, 1),
        fat_g=round(food.fat_g * servings, 1),
        target_calories=round(target_kcal),
        swapped=swapped,
    )


def _pick(candidates: list[Food], index: int, used: set[str]) -> Food:
    n = len(candidates)
    for offset in range(n):
        food = candidates[(index + offset) % n]
        if food.id not in used:
            return food
    return candidates[index % n]


def build_diet_plan(
    profile: BodyProfile, metrics: HealthMetrics, day: date, swaps: Swaps | None = None
) -> DietPlan:
    foods = eligible_foods(profile)
    seed = day.toordinal()

    # Ignore swaps that no longer fit (e.g. the user changed their diet type or allergies).
    valid_swaps: Swaps = {}
    for (meal_type, slot), food_id in (swaps or {}).items():
        if meal_type in MEAL_ROLES and 0 <= slot < len(MEAL_ROLES[meal_type]):
            if any(f.id == food_id for f in slot_candidates(foods, meal_type, slot)):
                valid_swaps[(meal_type, slot)] = food_id

    used: set[str] = set(valid_swaps.values())
    meals: list[PlannedMeal] = []

    for meal_index, (meal_type, share) in enumerate(MEAL_SPLIT.items()):
        meal_kcal = metrics.target_calories * share
        meal = PlannedMeal(meal_type=meal_type, target_calories=round(meal_kcal))

        roles = [
            (slot, candidates, weight)
            for slot, (_, weight) in enumerate(MEAL_ROLES[meal_type])
            if (candidates := slot_candidates(foods, meal_type, slot))
        ]
        total_weight = sum(w for _, _, w in roles)

        for slot, candidates, weight in roles:
            swapped_id = valid_swaps.get((meal_type, slot))
            if swapped_id:
                food = FOODS_BY_ID[swapped_id]
            else:
                food = _pick(candidates, seed + meal_index * 7 + slot * 3, used)
                used.add(food.id)
            meal.items.append(
                planned_item(food, slot, meal_kcal * weight / total_weight, swapped=bool(swapped_id))
            )
        meal.calories = round(sum(i.calories for i in meal.items))
        meals.append(meal)

    items = [i for m in meals for i in m.items]
    tips = list(GOAL_TIPS[metrics.effective_goal])
    if profile.diet_type in DIET_TIPS:
        tips.append(DIET_TIPS[profile.diet_type])
    tips.append(f"Drink about {metrics.water_liters} L of water per day.")

    return DietPlan(
        date=day,
        target_calories=metrics.target_calories,
        meals=meals,
        calories=round(sum(i.calories for i in items)),
        protein_g=round(sum(i.protein_g for i in items)),
        carbs_g=round(sum(i.carbs_g for i in items)),
        fat_g=round(sum(i.fat_g for i in items)),
        diet_type=profile.diet_type,
        excluded_allergens=sorted(profile.allergies),
        has_swaps=bool(valid_swaps),
        tips=tips,
    )


def swap_alternatives(plan: DietPlan, profile: BodyProfile, meal_type: str, slot: int) -> list[PlannedItem]:
    """Other foods that can fill this slot, scaled to the same calorie target."""
    meal = next(m for m in plan.meals if m.meal_type == meal_type)
    current = next((i for i in meal.items if i.slot == slot), None)
    if current is None:
        return []
    in_plan = {i.food_id for m in plan.meals for i in m.items}
    candidates = slot_candidates(eligible_foods(profile), meal_type, slot)
    return [
        planned_item(f, slot, current.target_calories)
        for f in sorted(candidates, key=lambda f: f.name)
        if f.id not in in_plan
    ]
