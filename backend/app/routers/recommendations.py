from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, Depends

from app.models import Profile
from app.schemas import DietPlanOut, WorkoutPlanOut
from app.security import get_current_profile
from app.services.diet import build_diet_plan
from app.services.health import compute_metrics
from app.services.workout import build_workout_plan

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/diet", response_model=DietPlanOut)
def diet_plan(day: date | None = None, profile: Profile = Depends(get_current_profile)) -> DietPlanOut:
    plan = build_diet_plan(profile, compute_metrics(profile), day or date.today())
    return DietPlanOut.model_validate(asdict(plan))


@router.get("/workout", response_model=WorkoutPlanOut)
def workout_plan(day: date | None = None, profile: Profile = Depends(get_current_profile)) -> WorkoutPlanOut:
    plan = build_workout_plan(profile, compute_metrics(profile), day or date.today())
    return WorkoutPlanOut.model_validate(asdict(plan))
