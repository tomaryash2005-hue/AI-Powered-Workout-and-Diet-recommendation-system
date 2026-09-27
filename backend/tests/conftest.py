import os
from collections.abc import Iterator

# Keep the app's own engine off the real database file; set before app modules load settings.
os.environ["FITAI_DATABASE_URL"] = "sqlite://"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.migrate import migrate  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    migrate(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db() -> Iterator[Session]:
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


PROFILE = {
    "age": 28,
    "sex": "male",
    "height_cm": 175,
    "weight_kg": 80,
    "activity_level": "moderate",
    "goal": "lose",
    "allergies": ["peanuts", "dairy"],
}


@pytest.fixture
def auth_client(client: TestClient) -> TestClient:
    res = client.post(
        "/api/auth/register",
        json={"name": "Test User", "email": "test@example.com", "password": "password123"},
    )
    client.headers["Authorization"] = f"Bearer {res.json()['access_token']}"
    return client


@pytest.fixture
def profiled_client(auth_client: TestClient) -> TestClient:
    auth_client.put("/api/profile", json=PROFILE)
    return auth_client
