from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.frontend import mount_frontend
from app.migrate import migrate
from app.routers import account, auth, foods, meals, notifications, profile, recommendations, weight, workouts


@asynccontextmanager
async def lifespan(_: FastAPI):
    migrate(engine)
    yield


app = FastAPI(title="FitAI – Workout & Diet Recommendations", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (
    auth.router,
    account.router,
    profile.router,
    recommendations.router,
    foods.router,
    meals.router,
    weight.router,
    workouts.router,
    notifications.router,
):
    app.include_router(r)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


DEFAULT_STATIC_DIR = Path(__file__).resolve().parents[2] / "web" / "dist"
static_dir = settings.static_dir or DEFAULT_STATIC_DIR
if (static_dir / "index.html").is_file():
    mount_frontend(app, static_dir)
