from dataclasses import dataclass, field
from datetime import date

from app.data.exercises import EQUIPMENT_LEVELS, EXERCISES, Exercise
from app.services.health import BodyProfile, HealthMetrics

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAYS_BY_ACTIVITY = {"sedentary": 3, "light": 3, "moderate": 4, "active": 5, "very_active": 5}
TRAINING_DAYS = {
    3: ["Monday", "Wednesday", "Friday"],
    4: ["Monday", "Tuesday", "Thursday", "Saturday"],
    5: ["Monday", "Tuesday", "Wednesday", "Friday", "Saturday"],
}
SPLITS = {
    "lose": {
        3: ["full_body", "cardio", "full_body"],
        4: ["full_body", "cardio", "full_body", "cardio"],
        5: ["full_body", "cardio", "full_body", "cardio", "cardio"],
    },
    "maintain": {
        3: ["full_body", "cardio", "full_body"],
        4: ["upper", "lower", "cardio", "full_body"],
        5: ["upper", "lower", "cardio", "upper", "lower"],
    },
    "gain": {
        3: ["full_body", "full_body", "full_body"],
        4: ["upper", "lower", "upper", "lower"],
        5: ["upper", "lower", "cardio", "upper", "lower"],
    },
}
SESSION_GROUPS = {
    "full_body": ["lower", "upper", "lower", "upper", "core"],
    "upper": ["upper", "upper", "upper", "core", "core"],
    "lower": ["lower", "lower", "lower", "lower", "core"],
}
SESSION_TITLES = {
    "full_body": "Full-body strength",
    "upper": "Upper body & core",
    "lower": "Lower body & core",
    "cardio": "Cardio",
    "rest": "Rest / active recovery",
}
SETS_REPS = {"lose": (3, "12–15"), "maintain": (3, "10–12"), "gain": (4, "8–12")}
CARDIO_MINUTES = {"lose": 40, "maintain": 30, "gain": 20}


@dataclass
class PlannedExercise:
    name: str
    sets: int
    reps: str
    rest_seconds: int
    tip: str


@dataclass
class WorkoutDay:
    day: str
    focus: str
    title: str
    duration_min: int
    exercises: list[PlannedExercise] = field(default_factory=list)


@dataclass
class WorkoutPlan:
    goal: str
    level: str
    low_impact: bool
    equipment: str
    days_per_week: int
    week: list[WorkoutDay]
    notes: list[str]


Pools = dict[str, list[list[Exercise]]]


def _choose(levels: list[list[Exercise]], used: set[str], index: int) -> Exercise:
    """Pick from the most equipment-specific level that still has unused exercises."""
    for pool in levels:
        remaining = [e for e in pool if e.id not in used]
        if remaining:
            return remaining[index % len(remaining)]
    raise ValueError("No exercises available")


def _strength_day(day: str, focus: str, pools: Pools, seed: int, goal: str, beginner: bool) -> WorkoutDay:
    sets, reps = SETS_REPS[goal]
    if beginner:
        sets = max(2, sets - 1)
    rest = 90 if goal == "gain" else 60
    hold = "20–30 s" if beginner else "30–45 s"

    used: set[str] = set()
    exercises: list[PlannedExercise] = []
    for i, group in enumerate(SESSION_GROUPS[focus]):
        ex = _choose(pools[group], used, seed + i)
        used.add(ex.id)
        exercises.append(PlannedExercise(ex.name, sets, hold if ex.timed else reps, rest, ex.tip))

    minutes = 10 + round(sum(e.sets for e in exercises) * (0.75 + rest / 60))
    return WorkoutDay(day, focus, SESSION_TITLES[focus], minutes, exercises)


def _cardio_day(day: str, pool: list[Exercise], seed: int, goal: str, beginner: bool) -> WorkoutDay:
    ex = pool[seed % len(pool)]
    minutes = 20 if ex.id == "hiit_circuit" else CARDIO_MINUTES[goal] - (10 if beginner else 0)
    return WorkoutDay(
        day, "cardio", SESSION_TITLES["cardio"], minutes,
        [PlannedExercise(ex.name, 1, f"{minutes} min", 0, ex.tip)],
    )


def build_workout_plan(profile: BodyProfile, metrics: HealthMetrics, day: date) -> WorkoutPlan:
    goal = metrics.effective_goal
    beginner = profile.activity_level in ("sedentary", "light")
    low_impact = metrics.bmi_category == "obese" or profile.age >= 60

    levels = EQUIPMENT_LEVELS[profile.equipment]
    exercises = [e for e in EXERCISES if not (low_impact and e.high_impact)]
    pools: Pools = {
        g: [[e for e in exercises if e.group == g and e.equipment == level] for level in levels]
        for g in ("upper", "lower", "core")
    }
    cardio = [e for level in levels for e in exercises if e.group == "cardio" and e.equipment == level]

    days_per_week = DAYS_BY_ACTIVITY[profile.activity_level]
    sessions = dict(zip(TRAINING_DAYS[days_per_week], SPLITS[goal][days_per_week]))
    week_seed = day.isocalendar().week

    week: list[WorkoutDay] = []
    for index, weekday in enumerate(WEEKDAYS):
        focus = sessions.get(weekday)
        seed = week_seed + index
        if focus is None:
            week.append(WorkoutDay(weekday, "rest", SESSION_TITLES["rest"], 20, [
                PlannedExercise("Easy walk + full-body stretching", 1, "20 min", 0,
                                "Keep it gentle — recovery is when you get stronger."),
            ]))
        elif focus == "cardio":
            week.append(_cardio_day(weekday, cardio, seed, goal, beginner))
        else:
            week.append(_strength_day(weekday, focus, pools, seed, goal, beginner))

    notes = [
        "Warm up for 5 minutes (light cardio + dynamic stretches) before each session.",
        "Cool down with 5 minutes of stretching afterwards.",
        "When the top of the rep range feels easy, move to a harder variation or add weight.",
    ]
    if low_impact:
        notes.append(
            "Your plan uses low-impact exercises only to protect your joints. "
            "Jumping movements are left out."
        )
    if profile.equipment != "none":
        notes.append(
            "Choose a weight where the last 2 reps of each set are hard but your form stays clean."
        )
    if beginner:
        notes.append("You're starting at a beginner volume — increase sets after 3–4 consistent weeks.")

    return WorkoutPlan(
        goal=goal,
        level="beginner" if beginner else "intermediate",
        low_impact=low_impact,
        equipment=profile.equipment,
        days_per_week=days_per_week,
        week=week,
        notes=notes,
    )
