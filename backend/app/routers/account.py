import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import (
    MealLog,
    PasswordResetToken,
    PlanSwap,
    Profile,
    PushSubscription,
    ReminderDelivery,
    ReminderSettings,
    User,
    WeightLog,
    WorkoutLog,
    WorkoutSet,
)
from app.routers.auth import user_out
from app.schemas import (
    ChangePasswordIn,
    DeleteAccountIn,
    ForgotPasswordIn,
    ResetPasswordIn,
    TokenOut,
)
from app.security import create_access_token, get_current_user, set_password, verify_password
from app.services.email import email_enabled, send_email

router = APIRouter(tags=["account"])

RESET_TOKEN_TTL = timedelta(hours=1)
MAX_RESETS_PER_HOUR = 3


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.post("/api/account/change-password", response_model=TokenOut)
def change_password(
    body: ChangePasswordIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TokenOut:
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password is incorrect")
    set_password(user, body.new_password)
    db.commit()
    # Other devices are signed out; this one gets a fresh session.
    return TokenOut(access_token=create_access_token(user), user=user_out(user))


@router.post("/api/auth/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    body: ForgotPasswordIn,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    # Same response whether or not the account exists, so emails can't be probed.
    reply = {"detail": "If an account exists for that email, we've sent a reset link."}
    if not email_enabled():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Password reset by email isn't set up")

    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None:
        return reply

    now = datetime.now(timezone.utc)
    recent = db.scalar(
        select(func.count())
        .select_from(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.created_at > now - timedelta(hours=1))
    )
    if recent >= MAX_RESETS_PER_HOUR:
        return reply

    token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id, token_hash=_hash_token(token), created_at=now, expires_at=now + RESET_TOKEN_TTL
        )
    )
    db.commit()

    base = (settings.public_url or str(request.base_url)).rstrip("/")
    link = f"{base}/reset-password?token={token}"
    background.add_task(
        send_email,
        user.email,
        "Reset your FitAI password",
        f"Hi {user.name},\n\nUse this link to choose a new password (valid for 1 hour):\n{link}\n\n"
        "If you didn't ask for this, you can ignore this email — your password won't change.",
    )
    return reply


@router.post("/api/auth/reset-password", response_model=TokenOut)
def reset_password(body: ResetPasswordIn, db: Session = Depends(get_db)) -> TokenOut:
    invalid = HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired")
    record = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash_token(body.token)))
    now = datetime.now(timezone.utc)
    if record is None or record.used_at is not None or _utc(record.expires_at) < now:
        raise invalid
    user = db.get(User, record.user_id)
    if user is None:
        raise invalid

    set_password(user, body.new_password)
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    db.commit()
    return TokenOut(access_token=create_access_token(user), user=user_out(user))


def _row(obj: Any, *fields: str) -> dict[str, Any]:
    out = {}
    for f in fields:
        value = getattr(obj, f)
        out[f] = value.isoformat() if hasattr(value, "isoformat") else value
    return out


@router.get("/api/account/export")
def export_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    uid = user.id
    profile = user.profile
    reminders = db.get(ReminderSettings, uid)
    data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "account": _row(user, "name", "email", "created_at"),
        "profile": _row(
            profile, "age", "sex", "height_cm", "weight_kg", "activity_level", "goal",
            "allergies", "diet_type", "bmi_standard", "equipment",
        ) if profile else None,
        "meals": [
            _row(m, "date", "meal_type", "name", "food_id", "servings", "calories",
                 "protein_g", "carbs_g", "fat_g", "allergens")
            for m in db.scalars(select(MealLog).where(MealLog.user_id == uid).order_by(MealLog.date, MealLog.id))
        ],
        "weigh_ins": [
            _row(w, "date", "weight_kg")
            for w in db.scalars(select(WeightLog).where(WeightLog.user_id == uid).order_by(WeightLog.date))
        ],
        "workouts": [
            {
                **_row(w, "date", "title", "duration_min", "notes"),
                "sets": [_row(s, "exercise", "set_number", "reps", "weight_kg", "duration_s") for s in w.sets],
            }
            for w in db.scalars(select(WorkoutLog).where(WorkoutLog.user_id == uid).order_by(WorkoutLog.date))
        ],
        "plan_swaps": [
            _row(p, "date", "meal_type", "slot", "food_id")
            for p in db.scalars(select(PlanSwap).where(PlanSwap.user_id == uid))
        ],
        "reminders": _row(
            reminders, "timezone", "meals_enabled", "breakfast_time", "lunch_time", "dinner_time",
            "weigh_in_enabled", "weigh_in_weekday", "weigh_in_time", "workout_enabled", "workout_time",
        ) if reminders else None,
    }
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="fitai-export.json"'},
    )


@router.delete("/api/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    body: DeleteAccountIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect password")
    uid = user.id
    workout_ids = select(WorkoutLog.id).where(WorkoutLog.user_id == uid)
    # Delete explicitly rather than relying on ON DELETE CASCADE, which SQLite doesn't enforce by default.
    db.execute(delete(WorkoutSet).where(WorkoutSet.workout_id.in_(workout_ids)))
    for model in (
        WorkoutLog, MealLog, WeightLog, PlanSwap, PasswordResetToken,
        PushSubscription, ReminderDelivery, ReminderSettings, Profile,
    ):
        db.execute(delete(model).where(model.user_id == uid))
    db.execute(delete(User).where(User.id == uid))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
