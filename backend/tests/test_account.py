import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.routers import account
from tests.conftest import PROFILE

DAY = "2026-09-27"


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    sent: list[dict[str, str]] = []

    def fake_send(to: str, subject: str, text: str) -> bool:
        sent.append({"to": to, "subject": subject, "text": text})
        return True

    monkeypatch.setattr(account, "send_email", fake_send)
    return sent


def reset_token(email: dict[str, str]) -> str:
    return re.search(r"token=([\w-]+)", email["text"]).group(1)


def login(client: TestClient, password: str) -> int:
    return client.post("/api/auth/login", json={"email": "test@example.com", "password": password}).status_code


def test_change_password_signs_out_other_sessions(auth_client: TestClient) -> None:
    c = auth_client
    old_header = c.headers["Authorization"]
    wrong = c.post("/api/account/change-password", json={"current_password": "nope", "new_password": "newpass123"})
    assert wrong.status_code == 400
    too_short = c.post("/api/account/change-password", json={"current_password": "password123", "new_password": "x"})
    assert too_short.status_code == 422

    res = c.post("/api/account/change-password", json={"current_password": "password123", "new_password": "newpass123"})
    assert res.status_code == 200
    assert c.get("/api/auth/me", headers={"Authorization": old_header}).status_code == 401
    new_header = f"Bearer {res.json()['access_token']}"
    assert c.get("/api/auth/me", headers={"Authorization": new_header}).status_code == 200
    assert login(c, "password123") == 401
    assert login(c, "newpass123") == 200


def test_forgot_and_reset_password(auth_client: TestClient, outbox: list[dict[str, str]]) -> None:
    c = auth_client
    old_header = c.headers.pop("Authorization")

    unknown = c.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert unknown.status_code == 202 and outbox == []

    res = c.post("/api/auth/forgot-password", json={"email": "Test@Example.com"})
    assert res.status_code == 202 and res.json() == unknown.json()
    assert len(outbox) == 1 and outbox[0]["to"] == "test@example.com"
    assert "/reset-password?token=" in outbox[0]["text"]
    token = reset_token(outbox[0])

    done = c.post("/api/auth/reset-password", json={"token": token, "new_password": "brandnew99"})
    assert done.status_code == 200 and done.json()["access_token"]
    assert c.post("/api/auth/reset-password", json={"token": token, "new_password": "again12345"}).status_code == 400
    assert c.get("/api/auth/me", headers={"Authorization": old_header}).status_code == 401
    assert login(c, "brandnew99") == 200


def test_reset_links_are_rate_limited_and_single_use(auth_client: TestClient, outbox: list[dict[str, str]]) -> None:
    c = auth_client
    for _ in range(5):
        c.post("/api/auth/forgot-password", json={"email": "test@example.com"})
    assert len(outbox) == account.MAX_RESETS_PER_HOUR
    first, second = reset_token(outbox[0]), reset_token(outbox[1])
    assert c.post("/api/auth/reset-password", json={"token": second, "new_password": "brandnew99"}).status_code == 200
    # Using one link invalidates the others.
    assert c.post("/api/auth/reset-password", json={"token": first, "new_password": "brandnew99"}).status_code == 400
    bogus = c.post("/api/auth/reset-password", json={"token": "x" * 43, "new_password": "brandnew99"})
    assert bogus.status_code == 400


def test_expired_reset_link(
    auth_client: TestClient, outbox: list[dict[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(account, "RESET_TOKEN_TTL", timedelta(seconds=-1))
    auth_client.post("/api/auth/forgot-password", json={"email": "test@example.com"})
    res = auth_client.post("/api/auth/reset-password", json={"token": reset_token(outbox[0]), "new_password": "brandnew99"})
    assert res.status_code == 400


def test_reset_unavailable_in_production_without_email(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "resend_api_key", None)
    assert client.get("/api/foods/options").json()["password_reset"] is False
    assert client.post("/api/auth/forgot-password", json={"email": "a@b.co"}).status_code == 503


def test_export_contains_all_user_data(profiled_client: TestClient) -> None:
    c = profiled_client
    c.post("/api/meals", json={"date": DAY, "meal_type": "lunch", "food_id": "tofu"})
    c.put("/api/weight", json={"date": DAY, "weight_kg": 79})
    c.post("/api/workouts", json={"date": DAY, "title": "Legs", "sets": [{"exercise": "Squat", "set_number": 1, "reps": 8, "weight_kg": 60}]})
    res = c.get("/api/account/export")
    assert res.status_code == 200
    assert "attachment" in res.headers["content-disposition"]
    data = res.json()
    assert data["account"]["email"] == "test@example.com"
    assert data["profile"]["allergies"] == sorted(PROFILE["allergies"])
    assert data["meals"][0]["name"] == "Firm tofu"
    assert {w["date"] for w in data["weigh_ins"]} >= {DAY}
    assert data["workouts"][0]["sets"][0]["weight_kg"] == 60
    assert "hashed_password" not in res.text


def test_delete_account_removes_everything(profiled_client: TestClient) -> None:
    c = profiled_client
    c.post("/api/meals", json={"date": DAY, "meal_type": "lunch", "food_id": "tofu"})
    c.post("/api/workouts", json={"date": DAY, "title": "Legs", "sets": [{"exercise": "Squat", "set_number": 1}]})
    c.put("/api/notifications/settings", json={"meals_enabled": True})
    assert c.request("DELETE", "/api/account", json={"password": "wrong"}).status_code == 400
    assert c.request("DELETE", "/api/account", json={"password": "password123"}).status_code == 204
    assert c.get("/api/auth/me").status_code == 401

    again = c.post("/api/auth/register", json={"name": "New", "email": "test@example.com", "password": "password123"})
    assert again.status_code == 201
    c.headers["Authorization"] = f"Bearer {again.json()['access_token']}"
    assert c.get("/api/meals", params={"day": DAY}).json() == []
    assert c.get("/api/workouts", params={"end": DAY}).json() == []
