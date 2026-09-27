import base64
import json
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.data.foods import FOODS_BY_ID
from app.services import ai_meals

PNG_1PX = base64.b64encode(
    bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
        "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
    )
).decode()


def claude_items(*items: dict[str, Any], notes: str = "") -> str:
    base = {
        "name": "", "serving": "", "servings": 1, "calories": 0, "protein_g": 0, "carbs_g": 0,
        "fat_g": 0, "allergens": [], "contains_meat": False, "jain_restricted": False, "confidence": "medium",
    }
    return json.dumps({"items": [{**base, **i} for i in items], "notes": notes})


class FakeClaude:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.reply = claude_items()
        self.stop_reason = "end_turn"
        self.error: Exception | None = None
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(
            stop_reason=self.stop_reason, content=[SimpleNamespace(type="text", text=self.reply)]
        )


@pytest.fixture
def claude(monkeypatch: pytest.MonkeyPatch) -> FakeClaude:
    fake = FakeClaude()
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(ai_meals, "_client", lambda key: fake)
    return fake


def parse(c: TestClient, **body: Any):
    return c.post("/api/ai/parse-meal", json={"meal_type": "lunch", **body})


def test_disabled_without_key(profiled_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    assert profiled_client.get("/api/foods/options").json()["ai_logging"] is False
    assert parse(profiled_client, text="2 rotis").status_code == 503


def test_request_uses_structured_output_and_fallbacks(profiled_client: TestClient, claude: FakeClaude) -> None:
    claude.reply = claude_items({"food_id": "roti", "servings": 1.5})
    assert parse(profiled_client, text="3 rotis").status_code == 200
    call = claude.calls[0]
    assert call["model"] == "claude-opus-5"
    assert call["fallbacks"] == "default" and call["betas"] == ["server-side-fallback-2026-07-01"]
    assert call["output_config"]["format"]["type"] == "json_schema"
    schema = call["output_config"]["format"]["schema"]
    assert "roti" in schema["properties"]["items"]["items"]["properties"]["food_id"]["enum"]
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"}
    user_text = call["messages"][0]["content"][-1]["text"]
    assert "<description>\n3 rotis\n</description>" in user_text and "Meal: lunch" in user_text


def test_reference_foods_use_trusted_nutrition(profiled_client: TestClient, claude: FakeClaude) -> None:
    # The model's numbers for a matched food are ignored in favour of the app's own data.
    claude.reply = claude_items({"food_id": "roti", "servings": 1.5, "calories": 9999, "confidence": "high"})
    data = parse(profiled_client, text="3 rotis").json()
    item = data["items"][0]
    roti = FOODS_BY_ID["roti"]
    assert item["food_id"] == "roti" and item["name"] == roti.name and item["servings"] == 1.5
    assert item["per_serving"]["calories"] == roti.calories
    assert item["allergens"] == ["gluten"] and item["confidence"] == "high"
    assert data["remaining_today"] == settings.ai_daily_limit - 1


def test_custom_foods_get_safety_checks(profiled_client: TestClient, claude: FakeClaude) -> None:
    # Profile: allergic to dairy and peanuts.
    claude.reply = claude_items(
        {"food_id": "none", "name": "Paneer tikka", "serving": "6 pieces (180 g)", "servings": 2,
         "calories": 560, "protein_g": 40, "carbs_g": 12, "fat_g": 38, "allergens": []},
        {"food_id": "none", "name": "Butter chicken", "serving": "1 bowl", "calories": 450,
         "allergens": ["dairy"], "contains_meat": True},
        notes="Couldn't tell how much oil was used.",
    )
    data = parse(profiled_client, text="paneer tikka and butter chicken").json()
    paneer, chicken = data["items"]
    assert paneer["food_id"] is None and paneer["servings"] == 2
    assert paneer["per_serving"]["calories"] == 280  # whole-portion estimate split per serving
    assert paneer["conflicts_with_allergies"] == ["dairy"]  # added from the name, not the model
    assert chicken["conflicts_with_allergies"] == ["dairy"] and chicken["fits_diet"] is True
    assert data["notes"] == "Couldn't tell how much oil was used."


def test_diet_conflicts_and_limits(auth_client: TestClient, claude: FakeClaude) -> None:
    auth_client.put("/api/profile", json={
        "age": 30, "sex": "female", "height_cm": 160, "weight_kg": 60, "activity_level": "light",
        "goal": "maintain", "allergies": [], "diet_type": "jain",
    })
    claude.reply = claude_items(
        {"food_id": "none", "name": "Aloo sabzi", "calories": 200, "servings": 100},
        {"food_id": "lentil_dal", "servings": 1},
        {"food_id": "none", "name": "Mystery", "calories": 999999, "confidence": "certain"},
    )
    aloo, dal, mystery = parse(auth_client, text="aloo sabzi, dal").json()["items"]
    assert aloo["fits_diet"] is False and aloo["servings"] == 20  # potato flagged by keyword; servings capped
    assert dal["fits_diet"] is False  # reference data: tadka with onion/garlic
    assert mystery["per_serving"]["calories"] == 5000 and mystery["confidence"] == "low"


def test_photo_is_sent_first_and_bad_photos_rejected(profiled_client: TestClient, claude: FakeClaude) -> None:
    ok = parse(profiled_client, image={"media_type": "image/png", "data": PNG_1PX})
    assert ok.status_code == 200
    content = claude.calls[0]["messages"][0]["content"]
    assert content[0]["type"] == "image" and content[0]["source"]["data"] == PNG_1PX
    assert "no description" in content[1]["text"]

    bad = parse(profiled_client, image={"media_type": "image/png", "data": "not base64!!"})
    assert bad.status_code == 422 and len(claude.calls) == 1
    assert parse(profiled_client, image={"media_type": "image/bmp", "data": PNG_1PX}).status_code == 422
    assert parse(profiled_client, text="   ").status_code == 422


def test_daily_limit(profiled_client: TestClient, claude: FakeClaude, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ai_daily_limit", 2)
    assert parse(profiled_client, text="a").json()["remaining_today"] == 1
    assert parse(profiled_client, text="b").json()["remaining_today"] == 0
    blocked = parse(profiled_client, text="c")
    assert blocked.status_code == 429 and len(claude.calls) == 2


def _api_error(cls: type[anthropic.APIStatusError], code: int) -> anthropic.APIStatusError:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("boom", response=httpx2.Response(code, request=request), body=None)


@pytest.mark.parametrize(
    "error, status",
    [
        (lambda: _api_error(anthropic.RateLimitError, 429), 503),
        (lambda: _api_error(anthropic.InternalServerError, 500), 502),
        (lambda: _api_error(anthropic.BadRequestError, 400), 422),
    ],
)
def test_api_errors_become_friendly_messages(
    profiled_client: TestClient, claude: FakeClaude, error: Any, status: int
) -> None:
    claude.error = error()
    res = parse(profiled_client, text="dal rice")
    assert res.status_code == status and "boom" not in res.json()["detail"]


def test_refusal_and_truncation(profiled_client: TestClient, claude: FakeClaude) -> None:
    claude.stop_reason = "refusal"
    assert parse(profiled_client, text="x").status_code == 422
    claude.stop_reason = "max_tokens"
    assert parse(profiled_client, text="x").status_code == 422
