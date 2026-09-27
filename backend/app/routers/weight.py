from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, WeightLog
from app.routers.profile import record_weight
from app.schemas import WeightIn, WeightOut
from app.security import get_current_user

router = APIRouter(prefix="/api/weight", tags=["weight"])


def _latest(db: Session, user_id: int) -> WeightLog | None:
    return db.scalar(
        select(WeightLog).where(WeightLog.user_id == user_id).order_by(WeightLog.date.desc()).limit(1)
    )


def _sync_profile(db: Session, user: User) -> None:
    """Keep the profile weight equal to the most recent weigh-in so plans stay current."""
    latest = _latest(db, user.id)
    if latest is not None and user.profile is not None:
        user.profile.weight_kg = latest.weight_kg


@router.get("", response_model=list[WeightOut])
def list_weights(
    end: date,
    days: int = Query(default=90, ge=1, le=730),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WeightLog]:
    start = end - timedelta(days=days - 1)
    return list(
        db.scalars(
            select(WeightLog)
            .where(WeightLog.user_id == user.id, WeightLog.date >= start, WeightLog.date <= end)
            .order_by(WeightLog.date)
        )
    )


@router.put("", response_model=WeightOut)
def log_weight(body: WeightIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> WeightLog:
    entry = record_weight(db, user.id, body.date, body.weight_kg)
    db.flush()
    _sync_profile(db, user)
    db.commit()
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_weight(entry_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    entry = db.get(WeightLog, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Weigh-in not found")
    db.delete(entry)
    db.flush()
    _sync_profile(db, user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
