"""Optional search of USDA FoodData Central (https://fdc.nal.usda.gov), enabled by FITAI_USDA_API_KEY.

USDA foods are only used for logging, never for generated plans, because allergen and diet
information is inferred from names and ingredient lists rather than curated.
"""

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.config import settings
from app.data.foods import Food

log = logging.getLogger(__name__)

BASE_URL = "https://api.nal.usda.gov/fdc/v1"
ID_PREFIX = "usda:"
TIMEOUT_SECONDS = 6

# Nutrient numbers (and newer nutrient ids) for the values we track, per 100 g.
NUTRIENT_KEYS: dict[str, tuple[str, ...]] = {
    "calories": ("208", "1008", "957", "958", "2047", "2048"),
    "protein_g": ("203", "1003"),
    "carbs_g": ("205", "1005"),
    "fat_g": ("204", "1004"),
}

KEYWORDS: dict[str, str] = {
    "dairy": r"(?<!coconut )(?<!almond )(?<!soy )(?<!oat )(?<!rice )milk|cheese|(?<!peanut )(?<!cocoa )(?<!nut )(?<!almond )butter\b|cream|whey|casein|"
    r"yogh?urt|ghee|paneer|lactose",
    "eggs": r"\beggs?\b|albumin|mayonnaise",
    "peanuts": r"peanut",
    "tree_nuts": r"almond|cashew|walnut|pecan|pistachio|hazelnut|macadamia|brazil nut",
    "soy": r"\bsoy|soya|tofu|edamame|tempeh",
    "gluten": r"wheat|barley|\brye\b|gluten|semolina|\bmalt|spelt|couscous|seitan",
    "fish": r"\bfish|salmon|tuna|\bcod\b|tilapia|sardine|anchov|mackerel|trout|haddock|pollock",
    "shellfish": r"shrimp|prawn|\bcrab|lobster|\bclams?\b|mussel|oyster|scallop|crayfish",
    "sesame": r"sesame|tahini",
    "meat": r"chicken|beef|pork|\blamb\b|mutton|turkey|bacon|\bham\b|sausage|salami|pepperoni|"
    r"veal|venison|\bduck\b|gelatin|lard",
    "jain_restricted": r"onion|garlic|potato|carrot|\bbeets?\b|beetroot|radish|ginger|turnip|\byams?\b|"
    r"shallot|\bleeks?\b|scallion|mushroom|honey",
}

DIET_FLAGS = ("meat", "jain_restricted")

_cache: dict[str, Food] = {}


def enabled() -> bool:
    return bool(settings.usda_api_key)


def _get(path: str, params: dict[str, Any]) -> Any:
    query = urllib.parse.urlencode({**params, "api_key": settings.usda_api_key}, doseq=True)
    with urllib.request.urlopen(f"{BASE_URL}{path}?{query}", timeout=TIMEOUT_SECONDS) as res:
        return json.load(res)


def _nutrient_values(raw: list[dict[str, Any]]) -> dict[str, float]:
    by_key: dict[str, float] = {}
    for n in raw:
        # Search results use flat keys; the details endpoint nests them under "nutrient".
        nested = n.get("nutrient") or {}
        number = str(n.get("nutrientNumber") or nested.get("number") or "")
        nid = str(n.get("nutrientId") or nested.get("id") or "")
        value = n.get("value", n.get("amount"))
        unit = (n.get("unitName") or nested.get("unitName") or "").lower()
        if value is None or unit == "kj":
            continue
        for key in (number, nid):
            if key:
                by_key.setdefault(key, float(value))

    values: dict[str, float] = {}
    for field, keys in NUTRIENT_KEYS.items():
        values[field] = next((round(by_key[k], 1) for k in keys if k in by_key), 0.0)
    return values


def detect_tags(text: str) -> tuple[tuple[str, ...], set[str]]:
    """Best-effort (allergens, diet flags) found in a food's name and ingredients."""
    text = text.lower()
    found = [k for k, pattern in KEYWORDS.items() if re.search(pattern, text)]
    allergens = tuple(k for k in found if k not in DIET_FLAGS)
    return allergens, {k for k in found if k in DIET_FLAGS}


def _to_food(item: dict[str, Any]) -> Food | None:
    if not item.get("fdcId"):
        return None
    values = _nutrient_values(item.get("foodNutrients") or [])
    if values["calories"] <= 0:
        return None
    name = str(item.get("description", "")).strip().capitalize()
    brand = item.get("brandName") or item.get("brandOwner")
    if brand:
        name = f"{name} ({str(brand).strip().title()})"
    allergens, flags = detect_tags(f"{item.get('description', '')} {item.get('ingredients', '')}")
    food = Food(
        id=f"{ID_PREFIX}{item['fdcId']}",
        name=name[:120],
        serving="100 g",
        category="external",
        meal_types=("breakfast", "lunch", "dinner", "snack"),
        allergens=allergens,
        meat="meat" in flags,
        jain_restricted="jain_restricted" in flags,
        **values,
    )
    if len(_cache) > 5000:
        _cache.clear()
    _cache[food.id] = food
    return food


def search(query: str, limit: int = 15) -> list[Food]:
    if not enabled() or len(query.strip()) < 3:
        return []
    try:
        data = _get(
            "/foods/search",
            {
                "query": query,
                "pageSize": limit,
                "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)", "Branded"],
            },
        )
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        log.warning("USDA search failed: %s", e)
        return []
    foods = [_to_food(item) for item in data.get("foods", [])]
    return [f for f in foods if f is not None]


def get_food(food_id: str) -> Food | None:
    if not enabled() or not food_id.startswith(ID_PREFIX):
        return None
    if food_id in _cache:
        return _cache[food_id]
    fdc_id = food_id.removeprefix(ID_PREFIX)
    if not fdc_id.isdigit():
        return None
    try:
        return _to_food(_get(f"/food/{fdc_id}", {}))
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as e:
        log.warning("USDA lookup failed for %s: %s", fdc_id, e)
        return None
