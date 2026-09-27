from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AiUsage, User
from app.schemas import AiParseIn, AiParseOut
from app.security import get_current_user
from app.services.ai_meals import AiMealError, ai_enabled, parse_meal

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _use_quota(db: Session, user: User) -> int:
    """Count this request against today's cap; returns how many remain afterwards."""
    today = datetime.now(timezone.utc).date()
    usage = db.get(AiUsage, (user.id, today))
    if usage is None:
        usage = AiUsage(user_id=user.id, day=today, count=0)
        db.add(usage)
    if usage.count >= settings.ai_daily_limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"You've used today's {settings.ai_daily_limit} AI requests. Log manually or try again tomorrow.",
        )
    usage.count += 1
    db.commit()
    return settings.ai_daily_limit - usage.count


@router.post("/parse-meal", response_model=AiParseOut)
def parse_meal_endpoint(
    body: AiParseIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> AiParseOut:
    if not ai_enabled():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI meal logging isn't set up on this server")
    remaining = _use_quota(db, user)
    profile = user.profile
    try:
        parsed = parse_meal(
            body.text,
            body.image,
            body.meal_type,
            allergies=profile.allergies if profile else [],
            diet_type=profile.diet_type if profile else "non_vegetarian",
        )
    except AiMealError as e:
        raise HTTPException(e.status, str(e))
    return AiParseOut(items=parsed.items, notes=parsed.notes, remaining_today=remaining)
