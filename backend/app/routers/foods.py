from fastapi import APIRouter, Depends

from app.data.exercises import EQUIPMENT
from app.data.foods import ALLERGENS, DIET_TYPES, FOODS, Food, fits_diet
from app.models import User
from app.schemas import FoodOut, MealType, OptionOut, OptionsOut
from app.security import get_current_user
from app.services import usda

router = APIRouter(prefix="/api/foods", tags=["foods"])


def food_out(food: Food, allergies: list[str], diet_type: str) -> FoodOut:
    return FoodOut(
        id=food.id,
        name=food.name,
        serving=food.serving,
        calories=food.calories,
        protein_g=food.protein_g,
        carbs_g=food.carbs_g,
        fat_g=food.fat_g,
        category=food.category,
        meal_types=list(food.meal_types),
        allergens=list(food.allergens),
        conflicts_with_allergies=sorted(set(food.allergens) & set(allergies)),
        fits_diet=fits_diet(food, diet_type),
        source="usda" if food.id.startswith(usda.ID_PREFIX) else "builtin",
    )


def _options(mapping: dict[str, str]) -> list[OptionOut]:
    return [OptionOut(key=k, label=v) for k, v in mapping.items()]


@router.get("/options", response_model=OptionsOut)
def list_options() -> OptionsOut:
    return OptionsOut(
        allergens=_options(ALLERGENS),
        diet_types=_options(DIET_TYPES),
        equipment=_options(EQUIPMENT),
        usda_search=usda.enabled(),
    )


@router.get("", response_model=list[FoodOut])
def search_foods(
    q: str = "",
    meal_type: MealType | None = None,
    user: User = Depends(get_current_user),
) -> list[FoodOut]:
    profile = user.profile
    allergies = profile.allergies if profile else []
    diet_type = profile.diet_type if profile else "non_vegetarian"
    term = q.strip().lower()
    foods = [
        f
        for f in FOODS
        if term in f.name.lower() and (meal_type is None or meal_type in f.meal_types)
    ]
    if term:
        foods += usda.search(term)
    return [food_out(f, allergies, diet_type) for f in foods]
