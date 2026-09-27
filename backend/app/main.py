from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.migrate import migrate
from app.routers import auth, foods, meals, profile, recommendations, weight


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

for r in (auth.router, profile.router, recommendations.router, foods.router, meals.router, weight.router):
    app.include_router(r)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
