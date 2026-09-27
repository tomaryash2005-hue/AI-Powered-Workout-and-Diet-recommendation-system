# FitAI – Workout & Diet Recommendation System

A web app that builds personalised workout and diet plans from a user's body measurements, goal, activity level, diet type (non-vegetarian, pescatarian, eggetarian, vegetarian, Jain or vegan) and food allergies, and lets them track meals and weight against their targets.

- **Backend:** Python + FastAPI + SQLAlchemy (SQLite by default, any SQLAlchemy database via `FITAI_DATABASE_URL`)
- **Web:** React + TypeScript + Vite, responsive and installable on phones (PWA)

## Features

- **Profile & BMI:** height, weight, age, sex, activity level, goal, diet type, allergies and workout equipment. BMI is calculated automatically and shown on either the international (WHO) scale or the Asian scale (overweight from 23, obese from 27.5), recommended for people of Asian descent.
- **Health metrics:** BMR (Mifflin-St Jeor), maintenance calories (TDEE), a goal-adjusted calorie target, protein/carb/fat targets, healthy weight range and water intake.
- **Diet types:** non-vegetarian, pescatarian (fish, no meat), eggetarian (vegetarian + eggs), vegetarian (no meat, fish or eggs; dairy OK), Jain (vegetarian without onion, garlic, ginger, potatoes or other root vegetables) and vegan (no animal products). Plans only use matching foods, and food search flags anything outside your diet.
- **Allergy-safe diet plan:** a daily breakfast/lunch/dinner/snack plan with portions scaled to the calorie target. Foods containing the user's allergens (dairy, eggs, peanuts, tree nuts, soy, gluten, fish, shellfish, sesame) are never suggested. The plan rotates day by day and draws on 115+ Indian and international foods.
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

After `npm run build`, the backend also serves the built app itself at http://localhost:8000. That's how it runs in production.

### Tests & checks

```bash
cd backend && .venv/bin/pytest     # backend unit + API tests (SQLite)
cd web && npm run lint && npm run build
```

To run the backend tests against Postgres as well, point `FITAI_TEST_POSTGRES_URL` at a **disposable** database (the tests wipe its `public` schema):

```bash
FITAI_TEST_POSTGRES_URL=postgresql://user:pass@localhost:5432/fitai_test .venv/bin/pytest
```

## Deploying

FitAI deploys as a **single Docker container** that serves both the API and the web app, plus a Postgres database. Migrations run automatically on every start.

### Render (one-click Blueprint)

The repo includes a [`render.yaml`](render.yaml) Blueprint that creates the web service and a Postgres database, and wires them together.

1. Sign in at [render.com](https://render.com) with your GitHub account.
2. **New → Blueprint**, pick this repository, and confirm. Render generates `FITAI_JWT_SECRET` and connects `DATABASE_URL` for you. `FITAI_USDA_API_KEY` is optional; leave it blank to skip USDA search.
3. Wait for the first build and deploy. Your app is then live at the `https://<name>.onrender.com` URL shown in the dashboard. Open it on your phone and use **Add to Home Screen** to install it.

Every push to `main` redeploys automatically. Render's free tier has limits: free web services sleep when idle, so the first visit after a while is slow, and free databases are time-limited. Check Render's pricing page, and move the database to a paid plan before relying on it for real data.

### Anywhere else that runs Docker

```bash
docker build -t fitai .
docker run -p 8000:8000 \
  -e FITAI_JWT_SECRET="$(openssl rand -hex 32)" \
  -e DATABASE_URL="postgres://user:pass@host:5432/fitai" \
  fitai
```

The image runs in production mode, so it refuses to start without a real `FITAI_JWT_SECRET`. Without `DATABASE_URL` it falls back to SQLite inside the container, which is lost when the container is replaced. Use Postgres for anything real. The container listens on `$PORT` (default 8000), as Railway, Fly.io and similar platforms expect.

## Configuration

Environment variables (or a `backend/.env` file):

| Variable | Default | Notes |
| --- | --- | --- |
| `FITAI_DATABASE_URL` or `DATABASE_URL` | `sqlite:///./fitai.db` | Postgres URLs such as `postgres://user:pass@host/db` work as given |
| `FITAI_JWT_SECRET` | dev placeholder | **Required in production:** a random value of at least 32 characters |
| `FITAI_ENVIRONMENT` | `development` | `production` (set in the Docker image) enforces a real secret |
| `FITAI_STATIC_DIR` | `web/dist` if built | Folder with the built web app for the backend to serve |
| `FITAI_CORS_ORIGINS` | `["http://localhost:5173"]` | JSON list |
| `FITAI_USDA_API_KEY` | unset | Free api.data.gov key (see the FoodData Central API guide) — enables USDA food search |

## Database migrations

The schema is managed with [Alembic](https://alembic.sqlalchemy.org). The backend applies any pending migrations automatically on startup, so updating the code and restarting upgrades the database without losing data.

When you change a model in `backend/app/models.py`, generate and review a migration:

```bash
cd backend
.venv/bin/alembic revision --autogenerate -m "describe the change"
# review migrations/versions/<new file>, then:
.venv/bin/alembic upgrade head      # or just restart the server
```

A test (`tests/test_migrations.py`) fails if the models and migrations drift apart. Databases created before migrations were added are adopted automatically. The exception is one from the very first version (before diet types), which has to be deleted (`backend/fitai.db`).

## Continuous integration

GitHub Actions (`.github/workflows/ci.yml`) runs on every pull request and every push to `main`. It runs:

- the backend tests on SQLite and on Postgres, including the migration checks
- the web app's lint, type check and build
- a Docker image build with a smoke test

## Disclaimer

FitAI gives general wellness guidance, not medical advice.
