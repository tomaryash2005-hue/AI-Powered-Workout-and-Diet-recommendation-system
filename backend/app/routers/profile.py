from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile, User
from app.schemas import MetricsOut, ProfileIn, ProfileOut
from app.security import get_current_profile, get_current_user
from app.services.health import compute_metrics

router = APIRouter(prefix="/api/profile", tags=["profile"])


def profile_out(profile: Profile) -> ProfileOut:
    return ProfileOut(
        age=profile.age,
        sex=profile.sex,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        activity_level=profile.activity_level,
        goal=profile.goal,
        allergies=profile.allergies,
        metrics=MetricsOut(**asdict(compute_metrics(profile))),
    )


@router.get("", response_model=ProfileOut)
def get_profile(profile: Profile = Depends(get_current_profile)) -> ProfileOut:
    return profile_out(profile)


@router.put("", response_model=ProfileOut)
def upsert_profile(
    body: ProfileIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileOut:
    if user.profile is None:
        user.profile = Profile(**body.model_dump())
    else:
        for key, value in body.model_dump().items():
            setattr(user.profile, key, value)
    db.commit()
    return profile_out(user.profile)
