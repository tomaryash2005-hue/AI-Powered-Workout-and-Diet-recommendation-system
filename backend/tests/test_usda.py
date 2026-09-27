from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.services import usda

SEARCH_RESPONSE = {
    "foods": [
        {
            "fdcId": 111,
            "description": "MILK CHOCOLATE BAR",
            "brandOwner": "ACME FOODS",
            "ingredients": "SUGAR, COCOA BUTTER, WHOLE MILK POWDER, SOY LECITHIN, ALMONDS",
            "foodNutrients": [
                {"nutrientNumber": "208", "unitName": "KCAL", "value": 535},
                {"nutrientNumber": "203", "unitName": "G", "value": 7.6},
                {"nutrientNumber": "205", "unitName": "G", "value": 59},
                {"nutrientNumber": "204", "unitName": "G", "value": 30},
            ],
        },
        {
            "fdcId": 222,
            "description": "Chicken, broilers or fryers, breast, roasted",
            "foodNutrients": [
                {"nutrientId": 1008, "unitName": "KCAL", "value": 165},
                {"nutrientId": 1003, "unitName": "G", "value": 31},
                {"nutrientId": 1005, "unitName": "G", "value": 0},
                {"nutrientId": 1004, "unitName": "G", "value": 3.6},
            ],
        },
        {"fdcId": 333, "description": "Water", "foodNutrients": []},
    ]
}

DETAIL_RESPONSE = {
    "fdcId": 444,
    "description": "Oat milk, unsweetened",
    "foodNutrients": [
        {"nutrient": {"id": 1008, "number": "208", "unitName": "kcal"}, "amount": 48},
        {"nutrient": {"id": 1003, "number": "203", "unitName": "g"}, "amount": 1},
        {"nutrient": {"id": 1005, "number": "205", "unitName": "g"}, "amount": 7},
        {"nutrient": {"id": 1004, "number": "204", "unitName": "g"}, "amount": 2},
    ],
}


@pytest.fixture
def fake_usda(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    def fake_get(path: str, params: dict[str, Any]) -> Any:
        calls.append(path)
        return SEARCH_RESPONSE if path == "/foods/search" else DETAIL_RESPONSE

    monkeypatch.setattr(settings, "usda_api_key", "test-key")
    monkeypatch.setattr(usda, "_get", fake_get)
    monkeypatch.setattr(usda, "_cache", {})
    return calls


def test_disabled_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "usda_api_key", None)
    assert usda.search("chocolate") == []
    assert usda.get_food("usda:111") is None


def test_search_parses_nutrients_and_tags(fake_usda: list[str]) -> None:
    foods = usda.search("chocolate")
    assert [f.id for f in foods] == ["usda:111", "usda:222"]
    bar, chicken = foods
    assert bar.name == "Milk chocolate bar (Acme Foods)"
    assert (bar.calories, bar.protein_g, bar.carbs_g, bar.fat_g) == (535, 7.6, 59, 30)
    assert set(bar.allergens) == {"dairy", "soy", "tree_nuts"}
    assert not bar.meat
    assert chicken.meat and chicken.calories == 165


@pytest.mark.parametrize(
    "text, allergens, flags",
    [
        ("Peanut butter, smooth", {"peanuts"}, set()),
        ("Butternut squash", set(), set()),
        ("Coconut milk, canned", set(), set()),
        ("Eggplant, raw", set(), set()),
        ("Scrambled eggs with butter", {"eggs", "dairy"}, set()),
        ("Ham and cheese sandwich on wheat bread", {"dairy", "gluten"}, {"meat"}),
        ("Shrimp tempura", {"shellfish"}, set()),
        ("Potato chips, sour cream and onion", {"dairy"}, {"jain_restricted"}),
        ("Chicken soup with garlic", set(), {"meat", "jain_restricted"}),
    ],
)
def test_detect_tags(text: str, allergens: set[str], flags: set[str]) -> None:
    found, found_flags = usda.detect_tags(text)
    assert set(found) == allergens and found_flags == flags


def test_logging_usda_food(profiled_client: TestClient, fake_usda: list[str]) -> None:
    c = profiled_client
    results = c.get("/api/foods", params={"q": "chocolate"}).json()
    bar = next(f for f in results if f["id"] == "usda:111")
    assert bar["source"] == "usda" and bar["conflicts_with_allergies"] == ["dairy"]

    logged = c.post(
        "/api/meals", json={"date": "2026-09-27", "meal_type": "snack", "food_id": "usda:111", "servings": 0.5}
    ).json()
    assert logged["calories"] == 267.5 and logged["allergy_warning"] == ["dairy"]

    # An id not seen in search is fetched from the details endpoint.
    oat = c.post("/api/meals", json={"date": "2026-09-27", "meal_type": "breakfast", "food_id": "usda:444"})
    assert oat.status_code == 201 and oat.json()["calories"] == 48
    assert fake_usda.count("/food/444") == 1
    bad = c.post("/api/meals", json={"date": "2026-09-27", "meal_type": "snack", "food_id": "usda:abc"})
    assert bad.status_code == 404


@pytest.mark.parametrize(
    "text, allergens, flags",
    [
        ("Aloo paratha", {"gluten"}, {"jain_restricted"}),
        ("Aalu gobi", set(), {"jain_restricted"}),
        ("Dahi vada", {"dairy"}, set()),
        ("Murgh makhani", {"dairy"}, {"meat"}),
        ("Kaju katli", {"tree_nuts"}, set()),
        ("Til ladoo", {"sesame"}, set()),
        ("Jhinga masala", {"shellfish"}, set()),
        ("Moong dal", set(), set()),
    ],
)
def test_detect_tags_indian_names(text: str, allergens: set[str], flags: set[str]) -> None:
    found, found_flags = usda.detect_tags(text)
    assert set(found) == allergens and found_flags == flags
