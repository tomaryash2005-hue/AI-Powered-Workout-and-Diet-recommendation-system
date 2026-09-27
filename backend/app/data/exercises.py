from dataclasses import dataclass

EQUIPMENT: dict[str, str] = {
    "none": "No equipment (bodyweight)",
    "dumbbells": "Home with dumbbells",
    "gym": "Full gym",
}

# Equipment levels a user can use, most specific first.
EQUIPMENT_LEVELS: dict[str, tuple[str, ...]] = {
    "none": ("none",),
    "dumbbells": ("dumbbells", "none"),
    "gym": ("gym", "dumbbells", "none"),
}


@dataclass(frozen=True)
class Exercise:
    id: str
    name: str
    group: str  # upper | lower | core | cardio
    equipment: str = "none"
    high_impact: bool = False
    timed: bool = False
    tip: str = ""


EXERCISES: list[Exercise] = [
    # --- Bodyweight: upper ---
    Exercise("push_ups", "Push-ups", "upper", tip="Drop to knees if you can't keep a straight line."),
    Exercise("incline_push_ups", "Incline push-ups", "upper", tip="Hands on a bench or wall to make it easier."),
    Exercise("pike_push_ups", "Pike push-ups", "upper", tip="Hips high, lower your head toward the floor."),
    Exercise("chair_dips", "Chair dips", "upper", tip="Keep elbows pointing back, not flared."),
    Exercise("superman", "Superman hold", "upper", timed=True, tip="Lift arms and legs, squeeze your back."),
    # --- Bodyweight: lower ---
    Exercise("squats", "Bodyweight squats", "lower", tip="Sit back like into a chair, knees over toes."),
    Exercise("reverse_lunges", "Reverse lunges", "lower", tip="Step back, lower the back knee gently."),
    Exercise("glute_bridges", "Glute bridges", "lower", tip="Squeeze glutes at the top for a second."),
    Exercise("step_ups", "Step-ups", "lower", tip="Use a sturdy step; drive through the front heel."),
    Exercise("wall_sit", "Wall sit", "lower", timed=True, tip="Thighs parallel to the floor if possible."),
    Exercise("calf_raises", "Calf raises", "lower", tip="Pause at the top, lower slowly."),
    Exercise("jump_squats", "Jump squats", "lower", high_impact=True, tip="Land softly with bent knees."),
    # --- Bodyweight: core ---
    Exercise("plank", "Plank", "core", timed=True, tip="Straight line from head to heels."),
    Exercise("dead_bug", "Dead bug", "core", tip="Keep your lower back pressed to the floor."),
    Exercise("bird_dog", "Bird dog", "core", tip="Move slowly, keep hips level."),
    Exercise("bicycle_crunches", "Bicycle crunches", "core", tip="Rotate from the torso, not the neck."),
    Exercise("mountain_climbers", "Mountain climbers", "core", high_impact=True, tip="Keep hips low and steady."),
    # --- Bodyweight: cardio ---
    Exercise("brisk_walk", "Brisk walking", "cardio", tip="Aim for a pace where talking is slightly hard."),
    Exercise("cycling", "Cycling (outdoor or stationary)", "cardio", tip="Moderate resistance, steady cadence."),
    Exercise("swimming", "Swimming", "cardio", tip="Any stroke; rest at the wall as needed."),
    Exercise("jogging", "Jogging", "cardio", high_impact=True, tip="Easy pace; alternate with walking if needed."),
    Exercise("hiit_circuit", "HIIT circuit (jumping jacks, high knees, burpees)", "cardio", high_impact=True,
             tip="30 s work / 30 s rest, repeat the circuit."),
    # --- Dumbbells ---
    Exercise("db_floor_press", "Dumbbell floor / bench press", "upper", "dumbbells",
             tip="Lower slowly until elbows touch the floor or reach bench level."),
    Exercise("db_row", "One-arm dumbbell row", "upper", "dumbbells", tip="Pull the elbow toward your hip."),
    Exercise("db_shoulder_press", "Dumbbell shoulder press", "upper", "dumbbells",
             tip="Brace your core; don't arch your lower back."),
    Exercise("db_curl", "Dumbbell biceps curl", "upper", "dumbbells", tip="Keep elbows pinned to your sides."),
    Exercise("db_triceps", "Overhead dumbbell triceps extension", "upper", "dumbbells",
             tip="Keep upper arms still and close to your head."),
    Exercise("goblet_squat", "Goblet squat", "lower", "dumbbells", tip="Hold the dumbbell at your chest, chest up."),
    Exercise("db_rdl", "Dumbbell Romanian deadlift", "lower", "dumbbells",
             tip="Push hips back with a flat back; feel the hamstrings."),
    Exercise("db_lunge", "Dumbbell split squat", "lower", "dumbbells", tip="Front knee tracks over the toes."),
    Exercise("db_step_up", "Dumbbell step-ups", "lower", "dumbbells", tip="Control the step down."),
    Exercise("db_russian_twist", "Dumbbell Russian twist", "core", "dumbbells",
             tip="Rotate slowly; keep feet down if needed."),
    # --- Gym ---
    Exercise("bench_press", "Barbell bench press", "upper", "gym", tip="Use a spotter or safety bars for heavy sets."),
    Exercise("lat_pulldown", "Lat pulldown", "upper", "gym", tip="Pull the bar to your upper chest, not behind the neck."),
    Exercise("cable_row", "Seated cable row", "upper", "gym", tip="Squeeze shoulder blades together at the end."),
    Exercise("machine_press", "Machine shoulder press", "upper", "gym", tip="Adjust the seat so handles start at shoulder height."),
    Exercise("triceps_pushdown", "Cable triceps pushdown", "upper", "gym", tip="Elbows stay by your sides."),
    Exercise("back_squat", "Barbell back squat", "lower", "gym", tip="Squat to a depth where your back stays neutral."),
    Exercise("leg_press", "Leg press", "lower", "gym", tip="Don't lock your knees at the top."),
    Exercise("barbell_rdl", "Barbell Romanian deadlift", "lower", "gym", tip="Bar stays close to your legs."),
    Exercise("leg_curl", "Lying leg curl", "lower", "gym", tip="Lower the weight slowly."),
    Exercise("leg_extension", "Leg extension", "lower", "gym", tip="Pause briefly at the top."),
    Exercise("cable_crunch", "Cable crunch", "core", "gym", tip="Curl your ribs toward your hips."),
    Exercise("hanging_knee_raise", "Hanging knee raise", "core", "gym", tip="Avoid swinging; move with control."),
    Exercise("incline_walk", "Incline treadmill walk", "cardio", "gym", tip="Don't hold the rails."),
    Exercise("rowing", "Rowing machine", "cardio", "gym", tip="Push with legs first, then pull with arms."),
    Exercise("elliptical", "Elliptical trainer", "cardio", "gym", tip="Keep a steady, moderate effort."),
    Exercise("stair_climber", "Stair climber", "cardio", "gym", tip="Stand tall; light hand contact only."),
]
