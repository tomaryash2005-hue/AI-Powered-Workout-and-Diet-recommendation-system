"""Approximate nutrition values per serving, compiled from common reference data."""

from dataclasses import dataclass

ALLERGENS: dict[str, str] = {
    "dairy": "Dairy / Milk",
    "eggs": "Eggs",
    "peanuts": "Peanuts",
    "tree_nuts": "Tree nuts",
    "soy": "Soy",
    "gluten": "Gluten / Wheat",
    "fish": "Fish",
    "shellfish": "Shellfish",
    "sesame": "Sesame",
}


@dataclass(frozen=True)
class Food:
    id: str
    name: str
    serving: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    category: str
    meal_types: tuple[str, ...]
    allergens: tuple[str, ...] = ()


FOODS: list[Food] = [
    # Protein sources
    Food("chicken_breast", "Grilled chicken breast", "100 g cooked", 165, 31, 0, 3.6, "protein", ("lunch", "dinner")),
    Food("salmon", "Baked salmon", "100 g cooked", 206, 22, 0, 12, "protein", ("lunch", "dinner"), ("fish",)),
    Food("tuna", "Tuna in water", "100 g drained", 116, 26, 0, 1, "protein", ("lunch", "dinner"), ("fish",)),
    Food("shrimp", "Grilled shrimp", "100 g cooked", 99, 24, 0.2, 0.3, "protein", ("lunch", "dinner"), ("shellfish",)),
    Food("lean_beef", "Lean ground beef (90%)", "100 g cooked", 217, 26, 0, 12, "protein", ("lunch", "dinner")),
    Food("paneer", "Paneer", "100 g", 300, 20, 4, 22, "protein", ("lunch", "dinner"), ("dairy",)),
    Food("tofu", "Firm tofu", "100 g", 144, 17, 3, 9, "protein", ("lunch", "dinner"), ("soy",)),
    Food("lentil_dal", "Lentil dal", "1 cup cooked", 260, 16, 38, 5, "protein", ("lunch", "dinner")),
    Food("chickpeas", "Chickpeas (chana)", "1 cup cooked", 269, 14.5, 45, 4.2, "protein", ("lunch", "dinner")),
    Food("rajma", "Kidney beans (rajma)", "1 cup cooked", 225, 15, 40, 0.9, "protein", ("lunch", "dinner")),
    # Breakfast mains
    Food("boiled_eggs", "Boiled eggs", "2 large", 155, 13, 1.1, 11, "protein", ("breakfast", "snack"), ("eggs",)),
    Food("veg_omelette", "Vegetable omelette", "2 eggs with vegetables", 200, 14, 4, 14, "protein", ("breakfast",), ("eggs",)),
    Food("greek_yogurt", "Greek yogurt, plain", "170 g", 100, 17, 6, 0.7, "protein", ("breakfast", "snack"), ("dairy",)),
    Food("besan_chilla", "Besan chilla", "2 medium", 240, 12, 30, 8, "mixed", ("breakfast",)),
    Food("idli_sambar", "Idli with sambar", "3 idlis + 1 cup sambar", 300, 12, 55, 4, "mixed", ("breakfast",)),
    Food("veg_poha", "Vegetable poha with peanuts", "1 plate", 250, 5, 40, 8, "mixed", ("breakfast",), ("peanuts",)),
    Food("avocado_toast", "Avocado toast", "1 slice whole-grain + ½ avocado", 240, 6, 22, 16, "mixed", ("breakfast",), ("gluten",)),
    Food("pb_toast", "Peanut butter toast", "1 slice + 1 tbsp", 174, 8, 17, 9, "mixed", ("breakfast", "snack"), ("peanuts", "gluten")),
    # Carbohydrates
    Food("oatmeal", "Oatmeal", "1 cup cooked", 166, 6, 28, 3.6, "carb", ("breakfast",), ("gluten",)),
    Food("brown_rice", "Brown rice", "1 cup cooked", 216, 5, 45, 1.8, "carb", ("lunch", "dinner")),
    Food("white_rice", "White rice", "1 cup cooked", 205, 4.3, 45, 0.4, "carb", ("lunch", "dinner")),
    Food("quinoa", "Quinoa", "1 cup cooked", 222, 8, 39, 3.6, "carb", ("lunch", "dinner")),
    Food("roti", "Whole-wheat roti", "2 medium", 210, 7, 36, 4, "carb", ("lunch", "dinner"), ("gluten",)),
    Food("sweet_potato", "Baked sweet potato", "1 medium", 135, 3, 31, 0.2, "carb", ("lunch", "dinner")),
    Food("ww_pasta", "Whole-wheat pasta", "1 cup cooked", 174, 7.5, 37, 0.8, "carb", ("lunch", "dinner"), ("gluten",)),
    # Vegetables
    Food("green_salad", "Green salad with olive oil", "1 bowl", 120, 2, 8, 9, "vegetable", ("lunch", "dinner")),
    Food("broccoli", "Steamed broccoli", "1 cup", 55, 3.7, 11, 0.6, "vegetable", ("lunch", "dinner")),
    Food("sauteed_veg", "Sautéed mixed vegetables", "1 cup", 100, 3, 12, 5, "vegetable", ("lunch", "dinner")),
    Food("palak_sabzi", "Spinach sabzi (palak)", "1 cup", 110, 5, 10, 6, "vegetable", ("lunch", "dinner")),
    # Fruit
    Food("apple", "Apple", "1 medium", 95, 0.5, 25, 0.3, "fruit", ("breakfast", "snack")),
    Food("banana", "Banana", "1 medium", 105, 1.3, 27, 0.4, "fruit", ("breakfast", "snack")),
    Food("berries", "Mixed berries", "1 cup", 85, 1, 21, 0.5, "fruit", ("breakfast", "snack")),
    Food("orange", "Orange", "1 medium", 62, 1.2, 15, 0.2, "fruit", ("breakfast", "snack")),
    # Dairy & snacks
    Food("milk", "Low-fat milk", "1 cup", 102, 8, 12, 2.4, "dairy", ("breakfast", "snack"), ("dairy",)),
    Food("almonds", "Almonds", "28 g (~23 nuts)", 164, 6, 6, 14, "snack", ("snack",), ("tree_nuts",)),
    Food("roasted_chana", "Roasted chana", "30 g", 120, 6.5, 18, 2, "snack", ("snack",)),
    Food("hummus_carrots", "Hummus with carrot sticks", "¼ cup + 1 cup carrots", 160, 5, 16, 9, "snack", ("snack",), ("sesame",)),
    Food("makhana", "Roasted makhana (fox nuts)", "30 g", 110, 3, 22, 1, "snack", ("snack",)),
]

FOODS_BY_ID: dict[str, Food] = {f.id: f for f in FOODS}
