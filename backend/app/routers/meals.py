from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.foods import FOODS_BY_ID
from app.database import get_db
from app.models import MealLog, Profile, User
from app.schemas import DailySummaryOut, MealLogIn, MealLogOut, NutrientProgress
from app.security import get_current_profile, get_current_user
from app.services.health import compute_metrics

router = APIRouter(prefix="/api/meals", tags=["meals"])


def meal_out(meal: MealLog, allergies: list[str]) -> MealLogOut:
    out = MealLogOut.model_validate(meal)
    out.allergy_warning = sorted(set(meal.allergens) & set(allergies))
    return out


def _meals_on(db: Session, user: User, day: date) -> list[MealLog]:
    return list(
        db.scalars(
            select(MealLog)
            .where(MealLog.user_id == user.id, MealLog.date == day)
            .order_by(MealLog.created_at)
        )
    )


def _allergies(user: User) -> list[str]:
    return user.profile.allergies if user.profile else []


@router.post("", response_model=MealLogOut, status_code=status.HTTP_201_CREATED)
def log_meal(
    body: MealLogIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MealLogOut:
    if body.food_id is not None:
        food = FOODS_BY_ID.get(body.food_id)
        if food is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Food not found")
        s = body.servings
        meal = MealLog(
            food_id=food.id,
            name=food.name,
            calories=round(food.calories * s, 1),
            protein_g=round(food.protein_g * s, 1),
            carbs_g=round(food.carbs_g * s, 1),
            fat_g=round(food.fat_g * s, 1),
            allergens=list(food.allergens),
        )
    else:
        # Custom entries are logged as the totals the user entered, regardless of servings.
        meal = MealLog(
            food_id=None,
            name=body.name.strip(),
            calories=body.calories,
            protein_g=body.protein_g,
            carbs_g=body.carbs_g,
            fat_g=body.fat_g,
            allergens=sorted(set(body.allergens)),
        )
    meal.user_id = user.id
    meal.date = body.date
    meal.meal_type = body.meal_type
    meal.servings = body.servings
    db.add(meal)
    db.commit()
    return meal_out(meal, _allergies(user))


@router.get("", response_model=list[MealLogOut])
def list_meals(
    day: date,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MealLogOut]:
    allergies = _allergies(user)
    return [meal_out(m, allergies) for m in _meals_on(db, user, day)]


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal(
    meal_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    meal = db.get(MealLog, meal_id)
    if meal is None or meal.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meal not found")
    db.delete(meal)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/summary", response_model=DailySummaryOut)
def daily_summary(
    day: date,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> DailySummaryOut:
    metrics = compute_metrics(profile)
    meals = _meals_on(db, user, day)

    def progress(attr: str, target: float) -> NutrientProgress:
        consumed = round(sum(getattr(m, attr) for m in meals), 1)
        return NutrientProgress(consumed=consumed, target=target, remaining=round(target - consumed, 1))

    return DailySummaryOut(
        date=day,
        calories=progress("calories", metrics.target_calories),
        protein_g=progress("protein_g", metrics.protein_g),
        carbs_g=progress("carbs_g", metrics.carbs_g),
        fat_g=progress("fat_g", metrics.fat_g),
        meals=[meal_out(m, profile.allergies) for m in meals],
    )
