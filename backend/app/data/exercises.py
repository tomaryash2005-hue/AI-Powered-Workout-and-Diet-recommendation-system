from dataclasses import dataclass


@dataclass(frozen=True)
class Exercise:
    id: str
    name: str
    group: str  # upper | lower | core | cardio
    high_impact: bool = False
    timed: bool = False
    tip: str = ""


EXERCISES: list[Exercise] = [
    # Upper body
    Exercise("push_ups", "Push-ups", "upper", tip="Drop to knees if you can't keep a straight line."),
    Exercise("incline_push_ups", "Incline push-ups", "upper", tip="Hands on a bench or wall to make it easier."),
    Exercise("pike_push_ups", "Pike push-ups", "upper", tip="Hips high, lower your head toward the floor."),
    Exercise("chair_dips", "Chair dips", "upper", tip="Keep elbows pointing back, not flared."),
    Exercise("superman", "Superman hold", "upper", timed=True, tip="Lift arms and legs, squeeze your back."),
    # Lower body
    Exercise("squats", "Bodyweight squats", "lower", tip="Sit back like into a chair, knees over toes."),
    Exercise("reverse_lunges", "Reverse lunges", "lower", tip="Step back, lower the back knee gently."),
    Exercise("glute_bridges", "Glute bridges", "lower", tip="Squeeze glutes at the top for a second."),
    Exercise("step_ups", "Step-ups", "lower", tip="Use a sturdy step; drive through the front heel."),
    Exercise("wall_sit", "Wall sit", "lower", timed=True, tip="Thighs parallel to the floor if possible."),
    Exercise("calf_raises", "Calf raises", "lower", tip="Pause at the top, lower slowly."),
    Exercise("jump_squats", "Jump squats", "lower", high_impact=True, tip="Land softly with bent knees."),
    # Core
    Exercise("plank", "Plank", "core", timed=True, tip="Straight line from head to heels."),
    Exercise("dead_bug", "Dead bug", "core", tip="Keep your lower back pressed to the floor."),
    Exercise("bird_dog", "Bird dog", "core", tip="Move slowly, keep hips level."),
    Exercise("bicycle_crunches", "Bicycle crunches", "core", tip="Rotate from the torso, not the neck."),
    Exercise("mountain_climbers", "Mountain climbers", "core", high_impact=True, tip="Keep hips low and steady."),
    # Cardio
    Exercise("brisk_walk", "Brisk walking", "cardio", tip="Aim for a pace where talking is slightly hard."),
    Exercise("cycling", "Cycling (outdoor or stationary)", "cardio", tip="Moderate resistance, steady cadence."),
    Exercise("swimming", "Swimming", "cardio", tip="Any stroke; rest at the wall as needed."),
    Exercise("jogging", "Jogging", "cardio", high_impact=True, tip="Easy pace; alternate with walking if needed."),
    Exercise("hiit_circuit", "HIIT circuit (jumping jacks, high knees, burpees)", "cardio", high_impact=True,
             tip="30 s work / 30 s rest, repeat the circuit."),
]
