from fastapi.testclient import TestClient

DAY = "2026-09-27"


def squat_session(day: str, weights: list[float]) -> dict:
    return {
        "date": day,
        "title": "Lower body & core",
        "duration_min": 40,
        "sets": [
            *({"exercise": "Goblet squat", "set_number": i + 1, "reps": 10, "weight_kg": w} for i, w in enumerate(weights)),
            {"exercise": "Plank", "set_number": 1, "duration_s": 45},
        ],
    }


def test_log_list_and_delete_workouts(auth_client: TestClient) -> None:
    c = auth_client
    res = c.post("/api/workouts", json=squat_session(DAY, [12, 14, 16]))
    assert res.status_code == 201
    workout = res.json()
    assert workout["title"] == "Lower body & core" and len(workout["sets"]) == 4
    assert workout["sets"][3] == {"exercise": "Plank", "set_number": 1, "reps": None, "weight_kg": None, "duration_s": 45}

    c.post("/api/workouts", json=squat_session("2026-09-20", [10]))
    listed = c.get("/api/workouts", params={"end": DAY, "days": 7}).json()
    assert [w["date"] for w in listed] == [DAY]
    assert len(c.get("/api/workouts", params={"end": DAY, "days": 30}).json()) == 2

    assert c.delete(f"/api/workouts/{workout['id']}").status_code == 204
    assert c.get("/api/workouts", params={"end": DAY, "days": 7}).json() == []


def test_strength_progress_tracks_heaviest_set(auth_client: TestClient) -> None:
    c = auth_client
    c.post("/api/workouts", json=squat_session("2026-09-20", [10, 12]))
    c.post("/api/workouts", json=squat_session(DAY, [12, 16, 14]))
    series = c.get("/api/workouts/strength", params={"end": DAY}).json()
    assert series == [
        {
            "exercise": "Goblet squat",
            "points": [
                {"date": "2026-09-20", "best_weight_kg": 12.0},
                {"date": DAY, "best_weight_kg": 16.0},
            ],
        }
    ]


def test_workout_validation_and_ownership(auth_client: TestClient) -> None:
    c = auth_client
    assert c.post("/api/workouts", json={"date": DAY, "title": ""}).status_code == 422
    bad_set = {"date": DAY, "title": "X", "sets": [{"exercise": "Squat", "set_number": 1, "weight_kg": -5}]}
    assert c.post("/api/workouts", json=bad_set).status_code == 422
    mine = c.post("/api/workouts", json={"date": DAY, "title": "Run"}).json()

    other = c.post("/api/auth/register", json={"name": "B", "email": "b@example.com", "password": "password123"})
    headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert c.delete(f"/api/workouts/{mine['id']}", headers=headers).status_code == 404
    assert c.get("/api/workouts", params={"end": DAY}, headers=headers).json() == []
