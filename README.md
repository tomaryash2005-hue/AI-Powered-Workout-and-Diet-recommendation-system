# FitAI – Workout & Diet Recommendation System

A web app that builds personalised workout and diet plans from a user's body measurements, goal, activity level, diet type (non-vegetarian to vegan) and food allergies, and lets them track meals and weight against their targets.

- **Backend:** Python + FastAPI + SQLAlchemy (SQLite by default, any SQLAlchemy database via `FITAI_DATABASE_URL`)
- **Web:** React + TypeScript + Vite, responsive and installable on phones (PWA)

## Features

- **Profile & BMI:** height, weight, age, sex, activity level, goal, diet type, allergies and workout equipment. BMI is calculated automatically and shown on either the international (WHO) scale or the Asian scale (overweight from 23, obese from 27.5), recommended for people of Asian descent.
- **Health metrics:** BMR (Mifflin-St Jeor), maintenance calories (TDEE), a goal-adjusted calorie target, protein/carb/fat targets, healthy weight range and water intake.
- **Diet types:** non-vegetarian, pescatarian (fish, no meat), eggetarian (vegetarian + eggs), vegetarian (no meat, fish or eggs; dairy OK) and vegan (no animal products). Plans only use matching foods, and food search flags anything outside your diet.
- **Allergy-safe diet plan:** a daily breakfast/lunch/dinner/snack plan with portions scaled to the calorie target. Foods containing the user's allergens (dairy, eggs, peanuts, tree nuts, soy, gluten, fish, shellfish, sesame) are never suggested. The plan rotates day by day and draws on 110+ Indian and international foods.
- **Swap a dish:** replace any dish in the plan with an alternative that fits the same spot, your diet and your allergies. Portions are rescaled to the same calories, and swaps are saved per day and can be undone.
- **Workout plan:** a weekly schedule based on goal, activity level and equipment (bodyweight, home dumbbells or full gym). It uses low-impact exercises when BMI is in the obese range or age ≥ 60, and beginner volume for sedentary or lightly active users.
- **Meal tracking:** log foods from the database or custom entries, log a whole planned meal in one click, see calories and macros eaten vs. remaining, and get a warning when a logged food contains one of your allergens or doesn't match your diet type.
- **Progress:** log weigh-ins (the latest one updates your profile weight and plans), and see a weight chart against your healthy range plus daily calories against your target over 7, 30 or 90 days.
- **USDA food search (optional):** set `FITAI_USDA_API_KEY` to also search the USDA FoodData Central database when logging. Their allergens and meat content are estimated from names and ingredient lists, so USDA foods are used for logging only, never for generated plans.
- **Installable app:** add FitAI to your phone's home screen from the browser (Share → Add to Home Screen on iOS, Install app on Android). The app shell works offline; your data always comes fresh from the server and is never cached.
- **Safety guardrails:** weight loss is blocked for underweight BMI, calories never go below a safe minimum, and the app suggests seeing a doctor at extreme BMIs.

## How the recommendations work

The engine is **rule-based**, so every number comes from a formula you can check. The logic lives in `backend/app/services/`:

| File | What it does |
| --- | --- |
| `health.py` | BMI (WHO or Asian cut-offs), BMR, TDEE, calorie target (−500 kcal to lose, +300 to gain), macro split, warnings |
| `diet.py` | Filters foods by diet type and allergens, builds each meal from protein, carb and vegetable slots, scales the servings, and applies saved swaps |
| `workout.py` | Picks the weekly split by goal and number of days, then chooses exercises for your equipment (filtered for impact) and sets/reps by goal |
| `usda.py` | Optional USDA FoodData Central search and lookup for logging |

The food and exercise data are in `backend/app/data/`. Nutrition values are approximate reference values.

## Running locally

### Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

### Web app

```bash
cd web
npm install
npm run dev
```

Open http://localhost:5173. The dev server forwards `/api` requests to the backend on port 8000.

### Tests & checks

```bash
cd backend && .venv/bin/pytest     # backend unit + API tests
cd web && npm run lint && npm run build
```

## Configuration

Environment variables (or a `backend/.env` file):

| Variable | Default | Notes |
| --- | --- | --- |
| `FITAI_DATABASE_URL` | `sqlite:///./fitai.db` | e.g. `postgresql+psycopg://user:pass@host/db` (install the driver) |
| `FITAI_JWT_SECRET` | dev placeholder | **Must be set to a long random value in production** |
| `FITAI_CORS_ORIGINS` | `["http://localhost:5173"]` | JSON list |
| `FITAI_USDA_API_KEY` | unset | Free api.data.gov key (see the FoodData Central API guide) — enables USDA food search |

> **Upgrading an existing local database:** tables are created automatically on startup, but existing tables aren't migrated. If you ran an earlier version, delete `backend/fitai.db` so it's recreated with the new columns.

## Disclaimer

FitAI gives general wellness guidance, not medical advice.
