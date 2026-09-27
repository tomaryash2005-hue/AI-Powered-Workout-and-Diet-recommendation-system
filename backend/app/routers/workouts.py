from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, WorkoutLog, WorkoutSet
from app.schemas import StrengthPoint, StrengthSeries, WorkoutIn, WorkoutOut
from app.security import get_current_user

router = APIRouter(prefix="/api/workouts", tags=["workouts"])


def _workouts_between(db: Session, user: User, start: date, end: date) -> list[WorkoutLog]:
    return list(
        db.scalars(
            select(WorkoutLog)
            .where(WorkoutLog.user_id == user.id, WorkoutLog.date >= start, WorkoutLog.date <= end)
            .order_by(WorkoutLog.date, WorkoutLog.id)
        )
    )


@router.post("", response_model=WorkoutOut, status_code=status.HTTP_201_CREATED)
def log_workout(body: WorkoutIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> WorkoutLog:
    workout = WorkoutLog(
        user_id=user.id,
        date=body.date,
        title=body.title.strip(),
        duration_min=body.duration_min,
        notes=body.notes.strip() if body.notes else None,
        sets=[WorkoutSet(**s.model_dump()) for s in body.sets],
    )
    db.add(workout)
    db.commit()
    return workout


@router.get("", response_model=list[WorkoutOut])
def list_workouts(
    end: date,
    days: int = Query(default=30, ge=1, le=366),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WorkoutLog]:
    return _workouts_between(db, user, end - timedelta(days=days - 1), end)


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    workout = db.get(WorkoutLog, workout_id)
    if workout is None or workout.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workout not found")
    db.delete(workout)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/strength", response_model=list[StrengthSeries])
def strength_progress(
    end: date,
    days: int = Query(default=90, ge=1, le=366),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[StrengthSeries]:
    """Heaviest weight lifted per exercise per day, for exercises logged with a weight."""
    best: dict[str, dict[date, float]] = defaultdict(dict)
    for workout in _workouts_between(db, user, end - timedelta(days=days - 1), end):
        for s in workout.sets:
            if s.weight_kg:
                day = best[s.exercise]
                day[workout.date] = max(day.get(workout.date, 0), s.weight_kg)
    return [
        StrengthSeries(
            exercise=name,
            points=[StrengthPoint(date=d, best_weight_kg=w) for d, w in sorted(points.items())],
        )
        for name, points in sorted(best.items())
    ]
