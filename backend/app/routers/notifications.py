import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import PushSubscription, ReminderSettings, User
from app.schemas import (
    PushSubscriptionIn,
    PushUnsubscribeIn,
    ReminderRunOut,
    ReminderSettingsIn,
    ReminderSettingsOut,
)
from app.security import get_current_user
from app.services.push import push_enabled
from app.services.reminders import RunResult, deliver, run_reminders

router = APIRouter(tags=["notifications"])


def _settings_out(db: Session, user: User) -> ReminderSettingsOut:
    s = db.get(ReminderSettings, user.id)
    devices = db.scalar(select(func.count()).select_from(PushSubscription).where(PushSubscription.user_id == user.id))
    base = ReminderSettingsOut.model_validate(s) if s else ReminderSettingsOut()
    return base.model_copy(update={"push_devices": devices})


@router.get("/api/notifications/settings", response_model=ReminderSettingsOut)
def get_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ReminderSettingsOut:
    return _settings_out(db, user)


@router.put("/api/notifications/settings", response_model=ReminderSettingsOut)
def save_settings(
    body: ReminderSettingsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ReminderSettingsOut:
    s = db.get(ReminderSettings, user.id)
    if s is None:
        db.add(ReminderSettings(user_id=user.id, **body.model_dump()))
    else:
        for key, value in body.model_dump().items():
            setattr(s, key, value)
    db.commit()
    return _settings_out(db, user)


@router.post("/api/notifications/subscriptions", status_code=status.HTTP_204_NO_CONTENT)
def subscribe(
    body: PushSubscriptionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    if not push_enabled():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Notifications aren't set up on this server")
    sub = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if sub is None:
        db.add(PushSubscription(user_id=user.id, endpoint=body.endpoint, p256dh=body.keys.p256dh, auth=body.keys.auth))
    else:
        # The same browser signed in to a different account now receives that account's reminders.
        sub.user_id, sub.p256dh, sub.auth = user.id, body.keys.p256dh, body.keys.auth
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/notifications/subscriptions/remove", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe(
    body: PushUnsubscribeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    sub = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if sub is not None and sub.user_id == user.id:
        db.delete(sub)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/notifications/test", response_model=ReminderRunOut)
def send_test(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ReminderRunOut:
    if not push_enabled():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Notifications aren't set up on this server")
    subs = list(db.scalars(select(PushSubscription).where(PushSubscription.user_id == user.id)))
    if not subs:
        raise HTTPException(status.HTTP_409_CONFLICT, "Turn on notifications on this device first")
    result = RunResult(users_checked=1)
    deliver(
        db,
        subs,
        {"title": "FitAI reminders are on", "body": "This is what your reminders will look like.", "url": "/", "tag": "test"},
        result,
    )
    return ReminderRunOut(**vars(result))


@router.post("/api/internal/reminders/run", response_model=ReminderRunOut, include_in_schema=False)
def run_due_reminders(
    x_cron_secret: str | None = Header(default=None), db: Session = Depends(get_db)
) -> ReminderRunOut:
    if not settings.cron_secret or not push_enabled():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not Found")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return ReminderRunOut(**vars(run_reminders(db, datetime.now(timezone.utc))))
