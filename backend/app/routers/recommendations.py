from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PlanSwap, Profile
from app.schemas import DietPlanOut, MealType, PlannedItemOut, SwapIn, WorkoutPlanOut
from app.security import get_current_profile
from app.services.diet import (
    MEAL_ROLES,
    DietPlan,
    build_diet_plan,
    eligible_foods,
    slot_candidates,
    swap_alternatives,
)
from app.services.health import compute_metrics
from app.services.workout import build_workout_plan

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def _plan(db: Session, profile: Profile, day: date) -> DietPlan:
    rows = db.scalars(select(PlanSwap).where(PlanSwap.user_id == profile.user_id, PlanSwap.date == day))
    swaps = {(r.meal_type, r.slot): r.food_id for r in rows}
    return build_diet_plan(profile, compute_metrics(profile), day, swaps)


def _check_slot(meal_type: str, slot: int) -> None:
    if slot >= len(MEAL_ROLES[meal_type]):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This meal has no such slot")


@router.get("/diet", response_model=DietPlanOut)
def diet_plan(
    day: date | None = None,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> DietPlanOut:
    return DietPlanOut.model_validate(asdict(_plan(db, profile, day or date.today())))


@router.get("/diet/alternatives", response_model=list[PlannedItemOut])
def diet_alternatives(
    day: date,
    meal_type: MealType,
    slot: int,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[PlannedItemOut]:
    _check_slot(meal_type, slot)
    plan = _plan(db, profile, day)
    return [PlannedItemOut.model_validate(asdict(i)) for i in swap_alternatives(plan, profile, meal_type, slot)]


@router.put("/diet/swap", response_model=DietPlanOut)
def swap_dish(
    body: SwapIn,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> DietPlanOut:
    _check_slot(body.meal_type, body.slot)
    allowed = {f.id for f in slot_candidates(eligible_foods(profile), body.meal_type, body.slot)}
    if body.food_id not in allowed:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "That food can't be used here — it doesn't fit this meal, your diet or your allergies",
        )
    key = (profile.user_id, body.day, body.meal_type, body.slot)
    swap = db.get(PlanSwap, key)
    if swap is None:
        db.add(PlanSwap(user_id=key[0], date=key[1], meal_type=key[2], slot=key[3], food_id=body.food_id))
    else:
        swap.food_id = body.food_id
    db.commit()
    return DietPlanOut.model_validate(asdict(_plan(db, profile, body.day)))


@router.delete("/diet/swaps", response_model=DietPlanOut)
def reset_swaps(
    day: date,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> DietPlanOut:
    db.execute(delete(PlanSwap).where(PlanSwap.user_id == profile.user_id, PlanSwap.date == day))
    db.commit()
    return DietPlanOut.model_validate(asdict(_plan(db, profile, day)))


@router.get("/workout", response_model=WorkoutPlanOut)
def workout_plan(day: date | None = None, profile: Profile = Depends(get_current_profile)) -> WorkoutPlanOut:
    plan = build_workout_plan(profile, compute_metrics(profile), day or date.today())
    return WorkoutPlanOut.model_validate(asdict(plan))
