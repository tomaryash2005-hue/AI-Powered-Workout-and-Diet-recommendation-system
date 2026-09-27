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

DIET_TYPES: dict[str, str] = {
    "non_vegetarian": "Non-vegetarian",
    "pescatarian": "Pescatarian (fish & seafood, no meat)",
    "eggetarian": "Eggetarian (vegetarian + eggs)",
    "vegetarian": "Vegetarian (no meat, fish or eggs)",
    "vegan": "Vegan (no animal products)",
}

# Animal products each diet leaves out. Fish, shellfish, eggs and dairy come from allergen tags.
DIET_EXCLUDES: dict[str, frozenset[str]] = {
    "non_vegetarian": frozenset(),
    "pescatarian": frozenset({"meat"}),
    "eggetarian": frozenset({"meat", "fish", "shellfish"}),
    "vegetarian": frozenset({"meat", "fish", "shellfish", "eggs"}),
    "vegan": frozenset({"meat", "fish", "shellfish", "eggs", "dairy"}),
}

ANIMAL_ALLERGENS = frozenset({"fish", "shellfish", "eggs", "dairy"})

# Categories the meal planner never picks from; these foods are only for logging.
LOG_ONLY_CATEGORIES = frozenset({"meal", "treat"})


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
    meat: bool = False

    @property
    def animal_products(self) -> frozenset[str]:
        found = ANIMAL_ALLERGENS.intersection(self.allergens)
        return found | {"meat"} if self.meat else found


def fits_diet(food: Food, diet_type: str) -> bool:
    return not food.animal_products & DIET_EXCLUDES[diet_type]


LD = ("lunch", "dinner")
B = ("breakfast",)
BS = ("breakfast", "snack")
S = ("snack",)

FOODS: list[Food] = [
    # --- Meat ---
    Food("chicken_breast", "Grilled chicken breast", "100 g cooked", 165, 31, 0, 3.6, "protein", LD, meat=True),
    Food("chicken_curry", "Chicken curry", "1 cup", 300, 28, 8, 17, "protein", LD, meat=True),
    Food("tandoori_chicken", "Tandoori chicken", "150 g", 225, 36, 5, 7, "protein", LD, ("dairy",), meat=True),
    Food("turkey_breast", "Roast turkey breast", "100 g", 135, 30, 0, 1, "protein", LD, meat=True),
    Food("lean_beef", "Lean ground beef (90%)", "100 g cooked", 217, 26, 0, 12, "protein", LD, meat=True),
    Food("pork_tenderloin", "Pork tenderloin", "100 g cooked", 143, 26, 0, 3.5, "protein", LD, meat=True),
    Food("mutton_curry", "Mutton curry", "1 cup", 330, 25, 6, 23, "protein", LD, meat=True),
    # --- Fish & seafood ---
    Food("salmon", "Baked salmon", "100 g cooked", 206, 22, 0, 12, "protein", LD, ("fish",)),
    Food("tuna", "Tuna in water", "100 g drained", 116, 26, 0, 1, "protein", LD, ("fish",)),
    Food("white_fish", "Grilled white fish (tilapia)", "100 g cooked", 128, 26, 0, 2.7, "protein", LD, ("fish",)),
    Food("fish_curry", "Fish curry", "1 cup", 250, 24, 6, 14, "protein", LD, ("fish",)),
    Food("shrimp", "Grilled shrimp", "100 g cooked", 99, 24, 0.2, 0.3, "protein", LD, ("shellfish",)),
    Food("prawn_curry", "Prawn curry", "1 cup", 230, 22, 8, 12, "protein", LD, ("shellfish",)),
    # --- Eggs ---
    Food("boiled_eggs", "Boiled eggs", "2 large", 155, 13, 1.1, 11, "protein", BS, ("eggs",)),
    Food("veg_omelette", "Vegetable omelette", "2 eggs with vegetables", 200, 14, 4, 14, "protein", B, ("eggs",)),
    Food("egg_bhurji", "Egg bhurji", "2 eggs", 220, 13, 5, 16, "protein", B, ("eggs",)),
    Food("egg_curry", "Egg curry", "2 eggs + gravy", 250, 14, 8, 18, "protein", LD, ("eggs",)),
    Food("egg_sandwich", "Egg sandwich (whole-wheat)", "1 sandwich", 300, 16, 30, 12, "mixed", B, ("eggs", "gluten")),
    # --- Dairy proteins ---
    Food("paneer", "Paneer (grilled or bhurji)", "100 g", 300, 20, 4, 22, "protein", LD, ("dairy",)),
    Food("palak_paneer", "Palak paneer", "1 cup", 280, 14, 10, 20, "protein", LD, ("dairy",)),
    Food("greek_yogurt", "Greek yogurt, plain", "170 g", 100, 17, 6, 0.7, "protein", BS, ("dairy",)),
    Food("cottage_cheese", "Low-fat cottage cheese", "1 cup", 163, 28, 6, 2.3, "protein", BS, ("dairy",)),
    # --- Plant proteins ---
    Food("tofu", "Firm tofu", "100 g", 144, 17, 3, 9, "protein", LD, ("soy",)),
    Food("tempeh", "Tempeh", "100 g", 192, 20, 8, 11, "protein", LD, ("soy",)),
    Food("soya_chunks", "Soya chunk curry", "1 cup", 220, 22, 18, 6, "protein", LD, ("soy",)),
    Food("edamame", "Edamame", "1 cup shelled", 188, 18.5, 14, 8, "protein", ("lunch", "dinner", "snack"), ("soy",)),
    Food("seitan", "Seitan", "100 g", 141, 25, 6, 2, "protein", LD, ("gluten",)),
    Food("lentil_dal", "Lentil dal (oil tadka)", "1 cup cooked", 260, 16, 38, 5, "protein", LD),
    Food("moong_dal", "Moong dal", "1 cup cooked", 210, 14, 34, 3, "protein", LD),
    Food("chana_masala", "Chana masala", "1 cup", 290, 12, 42, 9, "protein", LD),
    Food("chickpeas", "Chickpeas (boiled)", "1 cup cooked", 269, 14.5, 45, 4.2, "protein", LD),
    Food("rajma", "Rajma (kidney bean curry)", "1 cup", 240, 13, 38, 5, "protein", LD),
    Food("black_beans", "Black beans", "1 cup cooked", 227, 15, 41, 0.9, "protein", LD),
    # --- Breakfast dishes ---
    Food("besan_chilla", "Besan chilla", "2 medium", 240, 12, 30, 8, "mixed", B),
    Food("moong_chilla", "Moong dal chilla", "2 medium", 220, 14, 30, 5, "mixed", B),
    Food("tofu_scramble", "Tofu scramble with vegetables", "1 plate", 220, 18, 8, 13, "mixed", B, ("soy",)),
    Food("idli_sambar", "Idli with sambar", "3 idlis + 1 cup sambar", 300, 12, 55, 4, "mixed", B),
    Food("dosa_sambar", "Plain dosa with sambar", "1 dosa + 1 cup sambar", 300, 9, 48, 8, "mixed", B),
    Food("upma", "Vegetable upma", "1 cup", 250, 6, 38, 8, "mixed", B, ("gluten",)),
    Food("veg_poha", "Vegetable poha with peanuts", "1 plate", 250, 5, 40, 8, "mixed", B, ("peanuts",)),
    Food("aloo_paratha", "Aloo paratha (cooked in oil)", "1 medium", 290, 6, 40, 12, "mixed", B, ("gluten",)),
    Food("avocado_toast", "Avocado toast", "1 slice whole-grain + ½ avocado", 240, 6, 22, 16, "mixed", B, ("gluten",)),
    Food("pb_toast", "Peanut butter toast", "1 slice + 1 tbsp", 174, 8, 17, 9, "mixed", BS, ("peanuts", "gluten")),
    Food("overnight_oats", "Overnight oats with milk & fruit", "1 jar", 300, 12, 50, 7, "mixed", B, ("gluten", "dairy")),
    Food("soy_smoothie", "Banana soy-milk smoothie", "1 glass", 220, 9, 38, 4.5, "mixed", BS, ("soy",)),
    Food("chia_pudding", "Chia pudding (almond milk)", "1 cup", 250, 7, 22, 15, "mixed", BS, ("tree_nuts",)),
    # --- Carbohydrates ---
    Food("oatmeal", "Oatmeal (made with water)", "1 cup cooked", 166, 6, 28, 3.6, "carb", B, ("gluten",)),
    Food("dalia", "Dalia (broken wheat porridge)", "1 cup", 180, 6, 34, 2.5, "carb", B, ("gluten",)),
    Food("ragi_porridge", "Ragi porridge", "1 cup", 190, 5, 36, 3, "carb", B),
    Food("ww_bread", "Whole-wheat bread", "2 slices", 160, 8, 28, 2, "carb", B, ("gluten",)),
    Food("brown_rice", "Brown rice", "1 cup cooked", 216, 5, 45, 1.8, "carb", LD),
    Food("white_rice", "White rice", "1 cup cooked", 205, 4.3, 45, 0.4, "carb", LD),
    Food("quinoa", "Quinoa", "1 cup cooked", 222, 8, 39, 3.6, "carb", LD),
    Food("roti", "Whole-wheat roti", "2 medium", 210, 7, 36, 4, "carb", LD, ("gluten",)),
    Food("millet_roti", "Jowar / bajra roti", "2 medium", 220, 7, 44, 2.5, "carb", LD),
    Food("naan", "Naan", "1 piece", 262, 9, 45, 5, "carb", LD, ("gluten", "dairy")),
    Food("sweet_potato", "Baked sweet potato", "1 medium", 135, 3, 31, 0.2, "carb", LD),
    Food("potato", "Boiled potato", "1 medium", 161, 4.3, 37, 0.2, "carb", LD),
    Food("ww_pasta", "Whole-wheat pasta", "1 cup cooked", 174, 7.5, 37, 0.8, "carb", LD, ("gluten",)),
    Food("corn_tortillas", "Corn tortillas", "2 small", 110, 3, 23, 1.4, "carb", LD),
    # --- Vegetables ---
    Food("green_salad", "Green salad with olive oil", "1 bowl", 120, 2, 8, 9, "vegetable", LD),
    Food("kachumber", "Kachumber salad", "1 bowl", 50, 2, 10, 0.3, "vegetable", LD),
    Food("broccoli", "Steamed broccoli", "1 cup", 55, 3.7, 11, 0.6, "vegetable", LD),
    Food("green_beans", "Steamed green beans", "1 cup", 44, 2.4, 10, 0.4, "vegetable", LD),
    Food("sauteed_veg", "Sautéed mixed vegetables", "1 cup", 100, 3, 12, 5, "vegetable", LD),
    Food("mixed_veg_curry", "Mixed vegetable curry", "1 cup", 150, 4, 16, 8, "vegetable", LD),
    Food("palak_sabzi", "Spinach sabzi (palak)", "1 cup", 110, 5, 10, 6, "vegetable", LD),
    Food("bhindi", "Bhindi (okra) stir-fry", "1 cup", 130, 3, 12, 8, "vegetable", LD),
    Food("cabbage_sabzi", "Cabbage sabzi", "1 cup", 100, 3, 12, 5, "vegetable", LD),
    Food("baingan_bharta", "Baingan bharta", "1 cup", 140, 3, 15, 8, "vegetable", LD),
    Food("sambar", "Sambar", "1 cup", 130, 6, 20, 3, "vegetable", LD),
    # --- Fruit ---
    Food("apple", "Apple", "1 medium", 95, 0.5, 25, 0.3, "fruit", BS),
    Food("banana", "Banana", "1 medium", 105, 1.3, 27, 0.4, "fruit", BS),
    Food("berries", "Mixed berries", "1 cup", 85, 1, 21, 0.5, "fruit", BS),
    Food("orange", "Orange", "1 medium", 62, 1.2, 15, 0.2, "fruit", BS),
    Food("papaya", "Papaya", "1 cup", 62, 0.7, 16, 0.4, "fruit", BS),
    Food("mango", "Mango", "1 cup", 99, 1.4, 25, 0.6, "fruit", BS),
    Food("grapes", "Grapes", "1 cup", 104, 1.1, 27, 0.2, "fruit", BS),
    Food("pear", "Pear", "1 medium", 101, 0.6, 27, 0.2, "fruit", BS),
    Food("watermelon", "Watermelon", "2 cups", 90, 1.8, 23, 0.5, "fruit", BS),
    Food("guava", "Guava", "2 small", 75, 2.8, 16, 1, "fruit", BS),
    Food("pomegranate", "Pomegranate seeds", "½ cup", 72, 1.5, 16, 1, "fruit", BS),
    # --- Milk & alternatives ---
    Food("milk", "Low-fat milk", "1 cup", 102, 8, 12, 2.4, "dairy", BS, ("dairy",)),
    Food("curd", "Plain curd (dahi)", "1 cup", 150, 8.5, 11.4, 8, "dairy", BS, ("dairy",)),
    Food("buttermilk", "Buttermilk (chaas)", "1 glass", 60, 3, 5, 3, "dairy", BS, ("dairy",)),
    Food("soy_milk", "Soy milk, unsweetened", "1 cup", 80, 7, 4, 4, "dairy", BS, ("soy",)),
    Food("almond_milk", "Almond milk, unsweetened", "1 cup", 30, 1, 1, 2.5, "dairy", BS, ("tree_nuts",)),
    # --- Snacks ---
    Food("almonds", "Almonds", "28 g (~23 nuts)", 164, 6, 6, 14, "snack", S, ("tree_nuts",)),
    Food("walnuts", "Walnuts", "28 g", 185, 4.3, 3.9, 18.5, "snack", S, ("tree_nuts",)),
    Food("roasted_peanuts", "Roasted peanuts", "28 g", 166, 7, 6, 14, "snack", S, ("peanuts",)),
    Food("pumpkin_seeds", "Roasted pumpkin seeds", "28 g", 158, 8.5, 3, 14, "snack", S),
    Food("roasted_chana", "Roasted chana", "30 g", 120, 6.5, 18, 2, "snack", S),
    Food("sprouts_chaat", "Sprouts chaat", "1 bowl", 150, 9, 25, 2, "snack", S),
    Food("dhokla", "Khaman dhokla", "4 pieces", 160, 7, 22, 5, "snack", S),
    Food("hummus_carrots", "Hummus with carrot sticks", "¼ cup + 1 cup carrots", 160, 5, 16, 9, "snack", S, ("sesame",)),
    Food("makhana", "Roasted makhana (fox nuts)", "30 g", 110, 3, 22, 1, "snack", S),
    Food("popcorn", "Air-popped popcorn", "3 cups", 93, 3, 19, 1, "snack", S),
    Food("corn_chaat", "Sweet corn chaat", "1 cup", 140, 5, 30, 2, "snack", S),
    Food("apple_pb", "Apple with peanut butter", "1 apple + 1 tbsp", 190, 4.5, 28, 8.3, "snack", S, ("peanuts",)),
    # --- Complete dishes (logging only) ---
    Food("chicken_biryani", "Chicken biryani", "1 plate", 490, 25, 60, 16, "meal", LD, ("dairy",), meat=True),
    Food("veg_pulao", "Vegetable pulao", "1 cup", 240, 5, 40, 7, "meal", LD),
    Food("khichdi", "Moong dal khichdi", "1 cup", 230, 8, 40, 4, "meal", LD),
    Food("masala_dosa", "Masala dosa", "1 dosa", 390, 8, 55, 15, "meal", ("breakfast", "lunch", "dinner")),
    Food("pav_bhaji", "Pav bhaji", "1 plate", 400, 10, 55, 16, "meal", LD, ("gluten", "dairy")),
    Food("rajma_chawal", "Rajma chawal", "1 plate", 450, 16, 80, 6, "meal", LD),
    Food("pizza_slice", "Cheese pizza", "1 slice", 285, 12, 36, 10, "meal", LD, ("gluten", "dairy")),
    Food("chicken_wrap", "Grilled chicken wrap", "1 wrap", 350, 28, 35, 10, "meal", LD, ("gluten",), meat=True),
    # --- Treats (logging only) ---
    Food("samosa", "Samosa", "1 piece", 260, 4, 30, 14, "treat", S, ("gluten",)),
    Food("gulab_jamun", "Gulab jamun", "2 pieces", 300, 4, 45, 12, "treat", S, ("dairy", "gluten")),
    Food("masala_chai", "Masala chai with milk & sugar", "1 cup", 90, 3, 13, 3, "treat", BS, ("dairy",)),
    Food("dark_chocolate", "Dark chocolate (70%)", "20 g", 120, 1.6, 9, 8.5, "treat", S),
]

FOODS_BY_ID: dict[str, Food] = {f.id: f for f in FOODS}
