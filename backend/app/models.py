from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    # Bumped on password change/reset; sessions carrying an older version are rejected.
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    profile: Mapped["Profile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    meals: Mapped[list["MealLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    age: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str] = mapped_column(String(10))
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    activity_level: Mapped[str] = mapped_column(String(20))
    goal: Mapped[str] = mapped_column(String(20))
    allergies: Mapped[list[str]] = mapped_column(JSON, default=list)
    diet_type: Mapped[str] = mapped_column(String(20), default="non_vegetarian")
    bmi_standard: Mapped[str] = mapped_column(String(10), default="who")
    equipment: Mapped[str] = mapped_column(String(20), default="none")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    user: Mapped[User] = relationship(back_populates="profile")


class MealLog(Base):
    __tablename__ = "meal_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    meal_type: Mapped[str] = mapped_column(String(20))
    food_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    servings: Mapped[float] = mapped_column(Float)
    calories: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float)
    carbs_g: Mapped[float] = mapped_column(Float)
    fat_g: Mapped[float] = mapped_column(Float)
    allergens: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped[User] = relationship(back_populates="meals")


class WeightLog(Base):
    __tablename__ = "weight_logs"
    __table_args__ = (UniqueConstraint("user_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date)
    weight_kg: Mapped[float] = mapped_column(Float)


class PlanSwap(Base):
    """A user's replacement of one dish in the generated diet plan for a given day."""

    __tablename__ = "plan_swaps"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    meal_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    slot: Mapped[int] = mapped_column(Integer, primary_key=True)
    food_id: Mapped[str] = mapped_column(String(50))


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # Only a SHA-256 hash is stored, so a leaked database can't be used to reset passwords.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkoutLog(Base):
    __tablename__ = "workout_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(100))
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    sets: Mapped[list["WorkoutSet"]] = relationship(
        cascade="all, delete-orphan", order_by="WorkoutSet.id", lazy="selectin"
    )


class WorkoutSet(Base):
    __tablename__ = "workout_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workout_logs.id", ondelete="CASCADE"), index=True)
    exercise: Mapped[str] = mapped_column(String(120))
    set_number: Mapped[int] = mapped_column(Integer)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ReminderSettings(Base):
    __tablename__ = "reminder_settings"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    meals_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    breakfast_time: Mapped[str] = mapped_column(String(5), default="08:30")
    lunch_time: Mapped[str] = mapped_column(String(5), default="13:00")
    dinner_time: Mapped[str] = mapped_column(String(5), default="20:00")
    weigh_in_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    weigh_in_weekday: Mapped[int] = mapped_column(Integer, default=0)
    weigh_in_time: Mapped[str] = mapped_column(String(5), default="07:30")
    workout_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    workout_time: Mapped[str] = mapped_column(String(5), default="18:00")


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    endpoint: Mapped[str] = mapped_column(String(1000), unique=True)
    p256dh: Mapped[str] = mapped_column(String(200))
    auth: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ReminderDelivery(Base):
    """Marks a reminder as handled for a user's local day, so each fires at most once."""

    __tablename__ = "reminder_deliveries"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)
    local_date: Mapped[date] = mapped_column(Date, primary_key=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
