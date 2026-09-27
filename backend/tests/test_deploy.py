from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import DEV_JWT_SECRET, Settings, normalize_database_url
from app.frontend import mount_frontend


@pytest.mark.parametrize(
    "url, expected",
    [
        ("postgres://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
        ("postgresql://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("sqlite:///./fitai.db", "sqlite:///./fitai.db"),
    ],
)
def test_normalize_database_url(url: str, expected: str) -> None:
    assert normalize_database_url(url) == expected


def test_platform_database_url_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FITAI_DATABASE_URL")
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@db/fitai")
    assert Settings().database_url == "postgresql+psycopg://u:p@db/fitai"


def test_production_requires_real_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FITAI_ENVIRONMENT", "production")
    with pytest.raises(ValidationError):
        Settings()
    monkeypatch.setenv("FITAI_JWT_SECRET", "short")
    with pytest.raises(ValidationError):
        Settings()
    monkeypatch.setenv("FITAI_JWT_SECRET", "x" * 40)
    assert Settings().jwt_secret != DEV_JWT_SECRET


@pytest.fixture
def spa(tmp_path: Path) -> TestClient:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app shell</html>")
    (dist / "assets" / "index-abc123.js").write_text("console.log(1)")
    (dist / "sw.js").write_text("// sw")
    (tmp_path / "secret.txt").write_text("do not serve")

    app = FastAPI()

    @app.get("/api/ping")
    def ping() -> dict[str, str]:
        return {"pong": "yes"}

    mount_frontend(app, dist)
    return TestClient(app)


def test_spa_serves_app_shell_for_client_routes(spa: TestClient) -> None:
    for path in ("/", "/diet", "/progress/anything"):
        res = spa.get(path)
        assert res.status_code == 200 and "app shell" in res.text
        assert res.headers["cache-control"] == "no-cache"
    assert spa.head("/diet").status_code == 200


def test_spa_serves_static_files(spa: TestClient) -> None:
    assert spa.get("/assets/index-abc123.js").text == "console.log(1)"
    sw = spa.get("/sw.js")
    assert sw.text == "// sw" and sw.headers["cache-control"] == "no-cache"


def test_api_routes_win_and_unknown_api_paths_404(spa: TestClient) -> None:
    assert spa.get("/api/ping").json() == {"pong": "yes"}
    res = spa.get("/api/nope")
    assert res.status_code == 404 and res.headers["content-type"] == "application/json"


def test_spa_does_not_serve_files_outside_dist(spa: TestClient) -> None:
    for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"):
        assert "do not serve" not in spa.get(path).text
