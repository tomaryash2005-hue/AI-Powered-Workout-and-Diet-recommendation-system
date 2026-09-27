from fastapi import APIRouter, Depends

from app.data.foods import ALLERGENS, FOODS, Food
from app.models import User
from app.schemas import AllergenOut, FoodOut, MealType
from app.security import get_current_user

router = APIRouter(prefix="/api/foods", tags=["foods"])


def food_out(food: Food, allergies: list[str]) -> FoodOut:
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
    )


@router.get("/allergens", response_model=list[AllergenOut])
def list_allergens() -> list[AllergenOut]:
    return [AllergenOut(key=k, label=v) for k, v in ALLERGENS.items()]


@router.get("", response_model=list[FoodOut])
def search_foods(
    q: str = "",
    meal_type: MealType | None = None,
    user: User = Depends(get_current_user),
) -> list[FoodOut]:
    allergies = user.profile.allergies if user.profile else []
    term = q.strip().lower()
    return [
        food_out(f, allergies)
        for f in FOODS
        if term in f.name.lower() and (meal_type is None or meal_type in f.meal_types)
    ]
