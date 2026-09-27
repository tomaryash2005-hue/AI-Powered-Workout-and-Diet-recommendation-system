from datetime import date, datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import MealLog, Profile, PushSubscription, ReminderSettings, User, WeightLog, WorkoutLog
from app.services import reminders
from app.services.push import public_key_for
from app.services.reminders import due_kinds, run_reminders
from app.vapid_keys import generate_private_key

# 2026-09-28 is a Monday. India is UTC+5:30, so 03:10 UTC is 08:40 local.
MONDAY_0840_IST = datetime(2026, 9, 28, 3, 10, tzinfo=timezone.utc)


@pytest.fixture
def pushes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, Any]]]:
    sent: list[tuple[str, dict[str, Any]]] = []

    def fake_send(sub: PushSubscription, payload: dict[str, Any]) -> str:
        sent.append((sub.endpoint, payload))
        return "gone" if "expired" in sub.endpoint else "sent"

    monkeypatch.setattr(reminders, "send_push", fake_send)
    return sent


@pytest.fixture
def user(db_session: Session) -> User:
    u = User(email="r@example.com", name="R", hashed_password="x")
    u.profile = Profile(
        age=30, sex="female", height_cm=165, weight_kg=60, activity_level="moderate",
        goal="maintain", allergies=[], diet_type="vegetarian", bmi_standard="asian", equipment="none",
    )
    db_session.add(u)
    db_session.flush()
    db_session.add(ReminderSettings(
        user_id=u.id, timezone="Asia/Kolkata", meals_enabled=True, breakfast_time="08:30",
        lunch_time="13:00", dinner_time="20:00", weigh_in_enabled=True, weigh_in_weekday=0,
        weigh_in_time="07:30", workout_enabled=True, workout_time="08:00",
    ))
    db_session.add(PushSubscription(user_id=u.id, endpoint="https://push.example/phone", p256dh="k", auth="a"))
    db_session.commit()
    return u


def test_due_kinds_respects_times_weekday_and_window() -> None:
    s = ReminderSettings(
        meals_enabled=True, breakfast_time="08:30", lunch_time="13:00", dinner_time="20:00",
        weigh_in_enabled=True, weigh_in_weekday=0, weigh_in_time="07:30",
        workout_enabled=False, workout_time="08:00",
    )
    monday = datetime(2026, 9, 28, 8, 40)
    assert due_kinds(s, monday) == ["breakfast", "weigh_in"]
    assert due_kinds(s, monday.replace(hour=8, minute=29)) == ["weigh_in"]
    assert due_kinds(s, monday.replace(hour=11, minute=45)) == []  # more than 3 h late
    assert due_kinds(s, datetime(2026, 9, 29, 8, 40)) == ["breakfast"]  # Tuesday: no weigh-in


def test_run_sends_due_reminders_once(db_session: Session, user: User, pushes: list) -> None:
    result = run_reminders(db_session, MONDAY_0840_IST)
    titles = sorted(p["title"] for _, p in pushes)
    assert titles[0] == "Time to log breakfast"
    assert "Weekly weigh-in" in titles
    assert any(t.startswith("Workout today:") for t in titles)  # Monday is a training day
    assert result.sent == 3 and result.users_checked == 1

    again = run_reminders(db_session, MONDAY_0840_IST)
    assert again.sent == 0 and len(pushes) == 3


def test_already_done_tasks_are_not_reminded(db_session: Session, user: User, pushes: list) -> None:
    today = date(2026, 9, 28)
    db_session.add_all([
        MealLog(user_id=user.id, date=today, meal_type="breakfast", name="Poha", servings=1,
                calories=250, protein_g=5, carbs_g=40, fat_g=8, allergens=[]),
        WeightLog(user_id=user.id, date=today, weight_kg=60),
        WorkoutLog(user_id=user.id, date=today, title="Done"),
    ])
    db_session.commit()
    result = run_reminders(db_session, MONDAY_0840_IST)
    assert pushes == [] and result.skipped == 3


def test_rest_day_skips_workout_reminder(db_session: Session, user: User, pushes: list) -> None:
    sunday = datetime(2026, 9, 27, 3, 10, tzinfo=timezone.utc)
    run_reminders(db_session, sunday)
    assert not any(p["title"].startswith("Workout") for _, p in pushes)


def test_expired_subscriptions_are_removed(db_session: Session, user: User, pushes: list) -> None:
    db_session.add(PushSubscription(user_id=user.id, endpoint="https://push.example/expired", p256dh="k", auth="a"))
    db_session.commit()
    result = run_reminders(db_session, MONDAY_0840_IST)
    assert result.removed_subscriptions == 1
    endpoints = list(db_session.scalars(select(PushSubscription.endpoint)))
    assert endpoints == ["https://push.example/phone"]


def test_vapid_public_key_is_derived() -> None:
    key = public_key_for(generate_private_key())
    assert len(key) == 87 and key.startswith("B")  # 65-byte uncompressed P-256 point, base64url


@pytest.fixture
def push_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "vapid_private_key", generate_private_key())
    monkeypatch.setattr(settings, "cron_secret", "s3cret-value")


SUB = {"endpoint": "https://fcm.example/abc", "keys": {"p256dh": "BPk", "auth": "au"}}


def test_settings_api(auth_client: TestClient) -> None:
    c = auth_client
    defaults = c.get("/api/notifications/settings").json()
    assert defaults["meals_enabled"] is False and defaults["push_devices"] == 0
    saved = c.put("/api/notifications/settings", json={"timezone": "Asia/Kolkata", "meals_enabled": True, "lunch_time": "12:45"})
    assert saved.status_code == 200 and saved.json()["lunch_time"] == "12:45"
    assert c.put("/api/notifications/settings", json={"timezone": "Mars/Olympus"}).status_code == 422
    assert c.put("/api/notifications/settings", json={"lunch_time": "25:00"}).status_code == 422


def test_push_disabled_without_key(auth_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "vapid_private_key", None)
    assert auth_client.get("/api/foods/options").json()["push_public_key"] is None
    assert auth_client.post("/api/notifications/subscriptions", json=SUB).status_code == 503


def test_subscribe_test_and_unsubscribe(auth_client: TestClient, push_on: None, monkeypatch: pytest.MonkeyPatch) -> None:
    c = auth_client
    sent: list[str] = []
    monkeypatch.setattr(reminders, "send_push", lambda sub, payload: sent.append(payload["title"]) or "sent")
    assert c.get("/api/foods/options").json()["push_public_key"].startswith("B")
    assert c.post("/api/notifications/test").status_code == 409
    assert c.post("/api/notifications/subscriptions", json=SUB).status_code == 204
    assert c.post("/api/notifications/subscriptions", json=SUB).status_code == 204  # idempotent
    assert c.get("/api/notifications/settings").json()["push_devices"] == 1
    res = c.post("/api/notifications/test")
    assert res.status_code == 200 and res.json()["sent"] == 1 and sent == ["FitAI reminders are on"]
    c.post("/api/notifications/subscriptions/remove", json={"endpoint": SUB["endpoint"]})
    assert c.get("/api/notifications/settings").json()["push_devices"] == 0
    bad = {"endpoint": "http://insecure.example", "keys": SUB["keys"]}
    assert c.post("/api/notifications/subscriptions", json=bad).status_code == 422


def test_internal_run_requires_secret(client: TestClient, push_on: None, monkeypatch: pytest.MonkeyPatch) -> None:
    assert client.post("/api/internal/reminders/run").status_code == 403
    assert client.post("/api/internal/reminders/run", headers={"X-Cron-Secret": "wrong"}).status_code == 403
    ok = client.post("/api/internal/reminders/run", headers={"X-Cron-Secret": "s3cret-value"})
    assert ok.status_code == 200 and ok.json()["users_checked"] == 0
    monkeypatch.setattr(settings, "cron_secret", None)
    assert client.post("/api/internal/reminders/run", headers={"X-Cron-Secret": "s3cret-value"}).status_code == 404
