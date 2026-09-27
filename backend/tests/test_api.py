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


def test_options(client: TestClient) -> None:
    data = client.get("/api/foods/options").json()
    assert [d["key"] for d in data["diet_types"]] == [
        "non_vegetarian", "pescatarian", "eggetarian", "vegetarian", "jain", "vegan",
    ]
    assert {e["key"] for e in data["equipment"]} == {"none", "dumbbells", "gym"}
    assert data["usda_search"] is False


def test_profile_new_fields(auth_client: TestClient) -> None:
    body = {**PROFILE, "diet_type": "vegan", "bmi_standard": "asian", "equipment": "gym"}
    data = auth_client.put("/api/profile", json=body).json()
    assert data["diet_type"] == "vegan"
    assert data["metrics"]["bmi_standard"] == "asian"
    assert data["metrics"]["bmi_cutoffs"] == [18.5, 23.0, 27.5]
    assert data["metrics"]["bmi_category"] == "overweight"
    assert auth_client.put("/api/profile", json={**PROFILE, "diet_type": "keto"}).status_code == 422

    diet = auth_client.get("/api/recommendations/diet", params={"day": DAY}).json()
    assert diet["diet_type"] == "vegan"
    workout = auth_client.get("/api/recommendations/workout", params={"day": DAY}).json()
    assert workout["equipment"] == "gym"

    foods = auth_client.get("/api/foods", params={"q": "chicken"}).json()
    assert foods and not any(f["fits_diet"] for f in foods)


def test_swap_flow(profiled_client: TestClient) -> None:
    c = profiled_client
    plan = c.get("/api/recommendations/diet", params={"day": DAY}).json()
    assert plan["has_swaps"] is False
    original = plan["meals"][1]["items"][0]

    alts = c.get(
        "/api/recommendations/diet/alternatives", params={"day": DAY, "meal_type": "lunch", "slot": 0}
    ).json()
    assert alts and original["food_id"] not in {a["food_id"] for a in alts}
    choice = alts[-1]

    res = c.put(
        "/api/recommendations/diet/swap",
        json={"day": DAY, "meal_type": "lunch", "slot": 0, "food_id": choice["food_id"]},
    )
    assert res.status_code == 200
    item = res.json()["meals"][1]["items"][0]
    assert item["food_id"] == choice["food_id"] and item["swapped"]
    assert c.get("/api/recommendations/diet", params={"day": DAY}).json()["has_swaps"] is True
    other_day = c.get("/api/recommendations/diet", params={"day": "2026-09-28"}).json()
    assert other_day["has_swaps"] is False

    # Paneer conflicts with the dairy allergy, and a vegetable can't fill the protein slot.
    for food_id in ("paneer", "broccoli"):
        bad = c.put(
            "/api/recommendations/diet/swap",
            json={"day": DAY, "meal_type": "lunch", "slot": 0, "food_id": food_id},
        )
        assert bad.status_code == 422
    missing = c.get(
        "/api/recommendations/diet/alternatives", params={"day": DAY, "meal_type": "snack", "slot": 2}
    )
    assert missing.status_code == 404

    reset = c.delete("/api/recommendations/diet/swaps", params={"day": DAY}).json()
    assert reset["has_swaps"] is False
    assert reset["meals"][1]["items"][0]["food_id"] == original["food_id"]


def test_weight_tracking_updates_profile(auth_client: TestClient) -> None:
    c = auth_client
    c.put("/api/profile", json={**PROFILE, "as_of": "2026-09-01"})
    weights = c.get("/api/weight", params={"end": DAY}).json()
    assert [(w["date"], w["weight_kg"]) for w in weights] == [("2026-09-01", 80)]

    c.put("/api/weight", json={"date": "2026-09-20", "weight_kg": 78.5})
    c.put("/api/weight", json={"date": "2026-09-10", "weight_kg": 79.2})
    assert c.get("/api/profile").json()["weight_kg"] == 78.5

    updated = c.put("/api/weight", json={"date": "2026-09-20", "weight_kg": 78.0}).json()
    weights = c.get("/api/weight", params={"end": DAY}).json()
    assert [w["weight_kg"] for w in weights] == [80, 79.2, 78.0]

    assert c.delete(f"/api/weight/{updated['id']}").status_code == 204
    assert c.get("/api/profile").json()["weight_kg"] == 79.2

    # Saving the profile without changing weight doesn't add a weigh-in.
    c.put("/api/profile", json={**PROFILE, "weight_kg": 79.2, "goal": "gain", "as_of": DAY})
    assert len(c.get("/api/weight", params={"end": DAY}).json()) == 2
    assert c.put("/api/weight", json={"date": DAY, "weight_kg": 10}).status_code == 422


def test_calorie_history(profiled_client: TestClient) -> None:
    c = profiled_client
    c.post("/api/meals", json={"date": "2026-09-25", "meal_type": "lunch", "food_id": "tofu", "servings": 2})
    c.post("/api/meals", json={"date": DAY, "meal_type": "snack", "name": "Chai", "calories": 90})
    c.post("/api/meals", json={"date": DAY, "meal_type": "lunch", "name": "Thali", "calories": 700, "protein_g": 20})
    data = c.get("/api/meals/history", params={"end": DAY, "days": 7}).json()
    assert len(data["days"]) == 7
    assert data["days"][0]["date"] == "2026-09-21"
    by_date = {d["date"]: d for d in data["days"]}
    assert by_date["2026-09-25"]["calories"] == 288
    assert by_date[DAY]["calories"] == 790 and by_date[DAY]["protein_g"] == 20
    assert by_date["2026-09-26"]["calories"] == 0
    assert data["target_calories"] > 0
