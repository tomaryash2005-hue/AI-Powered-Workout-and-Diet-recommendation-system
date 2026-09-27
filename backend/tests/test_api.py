from fastapi.testclient import TestClient

from tests.conftest import PROFILE

DAY = "2026-09-27"


def test_register_login_and_me(client: TestClient) -> None:
    body = {"name": "Asha", "email": "Asha@Example.com", "password": "supersecret"}
    assert client.post("/api/auth/register", json=body).status_code == 201
    assert client.post("/api/auth/register", json=body).status_code == 409

    bad = client.post("/api/auth/login", json={"email": "asha@example.com", "password": "wrong-pass"})
    assert bad.status_code == 401

    res = client.post("/api/auth/login", json={"email": "asha@example.com", "password": "supersecret"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json() == {"id": 1, "name": "Asha", "email": "asha@example.com", "has_profile": False}


def test_endpoints_require_auth(client: TestClient) -> None:
    assert client.get("/api/profile").status_code == 401
    assert client.get("/api/meals", params={"day": DAY}).status_code == 401
    bad = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert bad.status_code == 401


def test_recommendations_require_profile(auth_client: TestClient) -> None:
    assert auth_client.get("/api/profile").status_code == 409
    assert auth_client.get("/api/recommendations/diet").status_code == 409


def test_profile_upsert_computes_bmi(auth_client: TestClient) -> None:
    res = auth_client.put("/api/profile", json=PROFILE)
    assert res.status_code == 200
    data = res.json()
    assert data["metrics"]["bmi"] == 26.1
    assert data["metrics"]["bmi_category"] == "overweight"
    assert data["allergies"] == ["dairy", "peanuts"]

    res = auth_client.put("/api/profile", json={**PROFILE, "weight_kg": 70})
    assert res.json()["metrics"]["bmi"] == 22.9
    assert auth_client.get("/api/auth/me").json()["has_profile"] is True


def test_profile_rejects_unknown_allergen(auth_client: TestClient) -> None:
    res = auth_client.put("/api/profile", json={**PROFILE, "allergies": ["kryptonite"]})
    assert res.status_code == 422


def test_diet_and_workout_plans(profiled_client: TestClient) -> None:
    diet = profiled_client.get("/api/recommendations/diet", params={"day": DAY}).json()
    assert [m["meal_type"] for m in diet["meals"]] == ["breakfast", "lunch", "dinner", "snack"]
    assert diet["excluded_allergens"] == ["dairy", "peanuts"]

    workout = profiled_client.get("/api/recommendations/workout", params={"day": DAY}).json()
    assert len(workout["week"]) == 7


def test_food_search_flags_allergies(profiled_client: TestClient) -> None:
    foods = profiled_client.get("/api/foods", params={"q": "paneer"}).json()
    assert foods[0]["conflicts_with_allergies"] == ["dairy"]
    snacks = profiled_client.get("/api/foods", params={"meal_type": "snack"}).json()
    assert all("snack" in f["meal_types"] for f in snacks)


def test_meal_logging_and_summary(profiled_client: TestClient) -> None:
    c = profiled_client
    res = c.post("/api/meals", json={"date": DAY, "meal_type": "lunch", "food_id": "paneer", "servings": 1.5})
    assert res.status_code == 201
    paneer = res.json()
    assert paneer["calories"] == 450
    assert paneer["allergy_warning"] == ["dairy"]

    custom = c.post(
        "/api/meals",
        json={"date": DAY, "meal_type": "snack", "name": "Homemade laddoo", "calories": 180, "fat_g": 9},
    )
    assert custom.status_code == 201

    assert c.post("/api/meals", json={"date": DAY, "meal_type": "snack"}).status_code == 422
    assert c.post("/api/meals", json={"date": DAY, "meal_type": "snack", "food_id": "nope"}).status_code == 404

    summary = c.get("/api/meals/summary", params={"day": DAY}).json()
    assert summary["calories"]["consumed"] == 630
    assert summary["calories"]["remaining"] == summary["calories"]["target"] - 630
    assert len(summary["meals"]) == 2

    assert c.delete(f"/api/meals/{paneer['id']}").status_code == 204
    assert len(c.get("/api/meals", params={"day": DAY}).json()) == 1
    assert c.get("/api/meals", params={"day": "2026-09-28"}).json() == []


def test_cannot_delete_other_users_meal(profiled_client: TestClient) -> None:
    meal = profiled_client.post(
        "/api/meals", json={"date": DAY, "meal_type": "lunch", "food_id": "tofu"}
    ).json()
    other = profiled_client.post(
        "/api/auth/register", json={"name": "B", "email": "b@example.com", "password": "password123"}
    ).json()["access_token"]
    res = profiled_client.delete(f"/api/meals/{meal['id']}", headers={"Authorization": f"Bearer {other}"})
    assert res.status_code == 404
