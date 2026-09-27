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
- **AI meal logging (optional):**
  - Type what you ate ("2 rotis, dal and some raita") or snap a photo of your plate. Claude identifies each food and portion.
  - You review and adjust the servings, or remove items, before anything is saved.
  - Foods matching the built-in list use FitAI's own nutrition data; anything else is marked "AI estimate".
  - Allergen and diet warnings apply as usual. A backup check on food names, including Hindi names like *aloo*, *paneer* and *atta*, adds any flags the AI missed.
- **Meal tracking:** log foods from the database or custom entries, log a whole planned meal in one click, see calories and macros eaten vs. remaining, and get a warning when a logged food contains one of your allergens or doesn't match your diet type.
- **Workout logging:** mark a planned session done and record reps and weights for each set (prefilled from the plan), with a weekly "done" counter.
- **Progress:**
  - Log weigh-ins; the latest one updates your profile weight and plans.
  - See charts over 7, 30 or 90 days: weight against your healthy range, daily calories against your target, and strength (heaviest set per exercise).
- **Reminders:** push notifications to log meals, a weekly weigh-in, and workouts on training days. Each reminder is skipped if you've already done it.
- **Account:**
  - Change your password, which signs out other devices.
  - Reset a forgotten password by email.
  - Export all your data as JSON, or permanently delete your account.
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

### Optional add-ons after deploying

Each of these is off until you configure it. The app works fine without them.

#### AI meal logging (Claude API)

1. Create an API key at [console.anthropic.com](https://console.anthropic.com) and add a little credit.
2. In Render → **fitai** → **Environment**, set `ANTHROPIC_API_KEY` to the key and save.

A **Describe** tab then appears first in the food log's *Add food* panel.

- **Model and fallback:** requests use Claude Opus 5 (`FITAI_AI_MODEL`). The API's server-side fallback is switched on, so the few requests Opus 5 declines are retried on another Claude model instead of failing.
- **Daily cap:** each user can make `FITAI_AI_DAILY_LIMIT` requests per day (default 30).
- **Cost:** it depends on your usage and current Anthropic pricing. Check the Usage page in the Anthropic Console after a few days. To spend less, lower the daily cap, or set `FITAI_AI_MODEL=claude-sonnet-5` for a cheaper model.
- **Privacy:** photos are shrunk on the device before upload and are not stored by FitAI.

#### Password-reset emails (Resend)

1. Create a free account at [resend.com](https://resend.com), verify a domain you own, and create an API key.
2. In Render → **fitai** → **Environment**, set:
   - `FITAI_RESEND_API_KEY` to the key.
   - `FITAI_EMAIL_FROM` to a sender on that domain, e.g. `FitAI <noreply@yourdomain.com>`.
3. Save. **Forgot password?** now appears on the sign-in page.

Links point at your Render address automatically (`RENDER_EXTERNAL_URL`). Set `FITAI_PUBLIC_URL` if you use a custom domain.

#### Reminders (push notifications)

1. Generate a key:

   ```bash
   cd backend && .venv/bin/python -m app.vapid_keys
   ```

2. In Render → **fitai** → **Environment**, set:
   - `FITAI_VAPID_PRIVATE_KEY` to the printed value.
   - `FITAI_VAPID_SUBJECT` to `mailto:you@example.com`.
3. Copy the value of `FITAI_CRON_SECRET` from the same page. Render generated it.
4. In GitHub → repo **Settings → Secrets and variables → Actions**, add two secrets:
   - `FITAI_APP_URL`: your `https://….onrender.com` address.
   - `FITAI_CRON_SECRET`: the value from step 3.
5. The **Reminders** workflow then calls the app every 15 minutes to send whatever is due. Each user turns reminders on in **Settings** (gear icon).

Some limits to know about:
- On iPhone, notifications only work after FitAI is added to the Home Screen.
- GitHub may run scheduled workflows a few minutes late, so reminders can arrive up to about 15–20 minutes after their set time. A reminder is still sent up to 3 hours late, but never twice.
- The scheduled calls keep a free Render service awake, which uses up its monthly free hours.

#### Daily encrypted backups

1. In Render → **fitai-db** → **Connections**, copy the **External Database URL**.
2. Make a long random passphrase, e.g. `openssl rand -base64 32`, and **store it somewhere safe**. Without it, backups can't be restored.
3. In GitHub → **Settings → Secrets and variables → Actions**, add two secrets:
   - `FITAI_BACKUP_DATABASE_URL`: the URL from step 1.
   - `FITAI_BACKUP_PASSPHRASE`: the passphrase from step 2.
4. The **Database backup** workflow then runs daily (and on demand from the Actions tab). It saves an AES-256-encrypted, compressed dump as a workflow artifact, kept for 30 days.

To restore, download the artifact and unzip it, then run:

```bash
export PASSPHRASE='your passphrase'
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:PASSPHRASE -in fitai-YYYYMMDD-HHMM.sql.gz.enc \
  | gunzip | psql "postgres://user:pass@host:5432/new_database"
```

Restore into an empty database running the same or a newer Postgres version. On an older version you may see a harmless `unrecognized configuration parameter` error at the start.

## Configuration

Environment variables (or a `backend/.env` file):

| Variable | Default | Notes |
| --- | --- | --- |
| `FITAI_DATABASE_URL` or `DATABASE_URL` | `sqlite:///./fitai.db` | Postgres URLs such as `postgres://user:pass@host/db` work as given |
| `FITAI_JWT_SECRET` | dev placeholder | **Required in production:** a random value of at least 32 characters |
| `FITAI_ENVIRONMENT` | `development` | `production` (set in the Docker image) enforces a real secret |
| `FITAI_STATIC_DIR` | `web/dist` if built | Folder with the built web app for the backend to serve |
| `FITAI_PUBLIC_URL` | `RENDER_EXTERNAL_URL` | Public address used in password-reset links |
| `FITAI_RESEND_API_KEY` / `FITAI_EMAIL_FROM` | unset | Password-reset emails. In development, emails are printed to the server log instead. |
| `FITAI_VAPID_PRIVATE_KEY` / `FITAI_VAPID_SUBJECT` | unset | Push reminders (`python -m app.vapid_keys`) |
| `FITAI_CRON_SECRET` | unset | Shared secret for the reminders scheduler |
| `ANTHROPIC_API_KEY` (or `FITAI_ANTHROPIC_API_KEY`) | unset | Turns on AI meal logging |
| `FITAI_AI_MODEL` / `FITAI_AI_DAILY_LIMIT` | `claude-opus-5` / `30` | Model for AI meal logging, and requests per user per day |
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

Two more workflows run on a schedule once their secrets are set: **Reminders** (every 15 minutes) and **Database backup** (daily). Both skip quietly until configured.

## Disclaimer

FitAI gives general wellness guidance, not medical advice.
