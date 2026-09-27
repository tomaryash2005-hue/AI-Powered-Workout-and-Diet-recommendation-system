from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile, User, WeightLog
from app.schemas import MetricsOut, ProfileIn, ProfileOut, ProfileSaveIn
from app.security import get_current_profile, get_current_user
from app.services.health import compute_metrics

router = APIRouter(prefix="/api/profile", tags=["profile"])

PROFILE_FIELDS = set(ProfileIn.model_fields)


def profile_out(profile: Profile) -> ProfileOut:
    fields = {name: getattr(profile, name) for name in PROFILE_FIELDS}
    return ProfileOut(**fields, metrics=MetricsOut(**asdict(compute_metrics(profile))))


def record_weight(db: Session, user_id: int, day: date, weight_kg: float) -> WeightLog:
    entry = db.scalar(select(WeightLog).where(WeightLog.user_id == user_id, WeightLog.date == day))
    if entry is None:
        entry = WeightLog(user_id=user_id, date=day, weight_kg=weight_kg)
        db.add(entry)
    else:
        entry.weight_kg = weight_kg
    return entry


@router.get("", response_model=ProfileOut)
def get_profile(profile: Profile = Depends(get_current_profile)) -> ProfileOut:
    return profile_out(profile)


@router.put("", response_model=ProfileOut)
def upsert_profile(
    body: ProfileSaveIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileOut:
    data = body.model_dump(include=PROFILE_FIELDS)
    weight_changed = user.profile is None or user.profile.weight_kg != body.weight_kg
    if user.profile is None:
        user.profile = Profile(**data)
    else:
        for key, value in data.items():
            setattr(user.profile, key, value)
    if weight_changed:
        record_weight(db, user.id, body.as_of or date.today(), body.weight_kg)
    db.commit()
    return profile_out(user.profile)
