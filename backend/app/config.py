from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-secret-set-FITAI_JWT_SECRET-in-production"


def normalize_database_url(url: str) -> str:
    """Hosting platforms hand out postgres:// URLs; SQLAlchemy needs the psycopg driver named."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


class Settings(BaseSettings):
    # Blank values (e.g. optional fields left empty in a hosting dashboard) count as unset.
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FITAI_", env_ignore_empty=True)

    environment: Literal["development", "production"] = "development"
    # DATABASE_URL is the name most hosting platforms use for an attached database.
    database_url: str = Field(
        default="sqlite:///./fitai.db",
        validation_alias=AliasChoices("FITAI_DATABASE_URL", "DATABASE_URL"),
    )
    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    usda_api_key: str | None = None
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    # Built web app to serve; defaults to ../web/dist when that exists.
    static_dir: Path | None = None
    # Public address of the app, used in password-reset links. Render sets RENDER_EXTERNAL_URL.
    public_url: str | None = Field(
        default=None, validation_alias=AliasChoices("FITAI_PUBLIC_URL", "RENDER_EXTERNAL_URL")
    )
    # Email (password reset) via Resend. Without a key, dev mode prints emails to the console.
    resend_api_key: str | None = None
    email_from: str = "FitAI <onboarding@resend.dev>"
    # Web push reminders. Generate a key with: python -m app.vapid_keys
    vapid_private_key: str | None = None
    vapid_subject: str = "mailto:admin@example.com"
    # Shared secret the scheduler sends to trigger reminders.
    cron_secret: str | None = None
    # AI meal logging (text and photo) via the Claude API. Off unless a key is set.
    anthropic_api_key: str | None = Field(
        default=None, validation_alias=AliasChoices("FITAI_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY")
    )
    ai_model: str = "claude-opus-5"
    # Per-user cap on AI requests per UTC day, to keep API costs predictable.
    ai_daily_limit: int = 30

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        return normalize_database_url(v)

    @model_validator(mode="after")
    def _require_real_secret_in_production(self) -> "Settings":
        if self.environment == "production" and (
            self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < 32
        ):
            raise ValueError("Set FITAI_JWT_SECRET to a random value of at least 32 characters in production")
        return self


settings = Settings()
