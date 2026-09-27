from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import MealLog, PushSubscription, ReminderDelivery, ReminderSettings, User, WeightLog, WorkoutLog
from app.services.health import compute_metrics
from app.services.push import send_push
from app.services.workout import build_workout_plan

# A reminder can still go out this long after its time, in case the scheduler ran late
# (for example while the server was waking up).
CATCH_UP = timedelta(hours=3)
MEALS = ("breakfast", "lunch", "dinner")


@dataclass
class RunResult:
    users_checked: int = 0
    sent: int = 0
    skipped: int = 0
    removed_subscriptions: int = 0


def _at(local_now: datetime, hhmm: str) -> datetime:
    hour, minute = map(int, hhmm.split(":"))
    return local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)


def due_kinds(s: ReminderSettings, local_now: datetime) -> list[str]:
    def due(hhmm: str) -> bool:
        start = _at(local_now, hhmm)
        return start <= local_now < start + CATCH_UP

    kinds = [m for m in MEALS if s.meals_enabled and due(getattr(s, f"{m}_time"))]
    if s.weigh_in_enabled and local_now.weekday() == s.weigh_in_weekday and due(s.weigh_in_time):
        kinds.append("weigh_in")
    if s.workout_enabled and due(s.workout_time):
        kinds.append("workout")
    return kinds


def build_message(db: Session, user: User, kind: str, day: date) -> dict[str, Any] | None:
    """The notification for a due reminder, or None when there's nothing to remind about."""
    if kind in MEALS:
        logged = db.scalar(
            select(MealLog.id).where(MealLog.user_id == user.id, MealLog.date == day, MealLog.meal_type == kind)
        )
        if logged:
            return None
        return {
            "title": f"Time to log {kind}",
            "body": f"Add what you ate, or log today's planned {kind} in one tap.",
            "url": "/diet",
            "tag": f"meal-{kind}",
        }

    if kind == "weigh_in":
        if db.scalar(select(WeightLog.id).where(WeightLog.user_id == user.id, WeightLog.date == day)):
            return None
        return {
            "title": "Weekly weigh-in",
            "body": "Log your weight to keep your plan and progress charts up to date.",
            "url": "/progress",
            "tag": "weigh-in",
        }

    if kind == "workout":
        profile = user.profile
        if profile is None:
            return None
        if db.scalar(select(WorkoutLog.id).where(WorkoutLog.user_id == user.id, WorkoutLog.date == day)):
            return None
        session = build_workout_plan(profile, compute_metrics(profile), day).week[day.weekday()]
        if session.focus == "rest":
            return None
        return {
            "title": f"Workout today: {session.title}",
            "body": f"About {session.duration_min} min · {len(session.exercises)} exercises. Tap to see your plan.",
            "url": "/workout",
            "tag": "workout",
        }

    raise ValueError(f"Unknown reminder kind: {kind}")


def _claim(db: Session, user_id: int, kind: str, day: date) -> bool:
    """Record the reminder as handled; False if another run already did."""
    if db.get(ReminderDelivery, (user_id, kind, day)) is not None:
        return False
    db.add(ReminderDelivery(user_id=user_id, kind=kind, local_date=day))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return False
    return True


def deliver(db: Session, subs: list[PushSubscription], message: dict[str, Any], result: RunResult) -> None:
    for sub in subs:
        outcome = send_push(sub, message)
        if outcome == "sent":
            result.sent += 1
        elif outcome == "gone":
            db.delete(sub)
            result.removed_subscriptions += 1
    db.commit()


def run_reminders(db: Session, now_utc: datetime) -> RunResult:
    result = RunResult()
    with_devices = select(PushSubscription.user_id)
    for s in list(db.scalars(select(ReminderSettings).where(ReminderSettings.user_id.in_(with_devices)))):
        result.users_checked += 1
        local_now = now_utc.astimezone(ZoneInfo(s.timezone))
        kinds = due_kinds(s, local_now)
        if not kinds:
            continue
        user = db.get(User, s.user_id)
        subs = list(db.scalars(select(PushSubscription).where(PushSubscription.user_id == s.user_id)))
        for kind in kinds:
            day = local_now.date()
            if not _claim(db, s.user_id, kind, day):
                continue
            message = build_message(db, user, kind, day)
            if message is None:
                result.skipped += 1
                continue
            deliver(db, subs, message, result)
            subs = [sub for sub in subs if sub in db]
    return result
