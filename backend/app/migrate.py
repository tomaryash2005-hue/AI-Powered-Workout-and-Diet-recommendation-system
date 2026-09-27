from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect
from sqlalchemy.engine import Connection

BACKEND_DIR = Path(__file__).resolve().parent.parent
BASELINE_REVISION = "0001"


class OutdatedDatabaseError(RuntimeError):
    pass


def alembic_config(connection: Connection | None = None) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.attributes["connection"] = connection
    return config


def _matches_baseline(conn: Connection) -> bool:
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())
    if not {"users", "profiles", "meal_logs", "weight_logs", "plan_swaps"} <= tables:
        return False
    profile_columns = {c["name"] for c in inspector.get_columns("profiles")}
    return {"diet_type", "bmi_standard", "equipment"} <= profile_columns


def migrate(engine: Engine) -> None:
    """Bring the database schema up to the latest migration."""
    with engine.begin() as conn:
        tables = set(inspect(conn).get_table_names())
        config = alembic_config(conn)
        if "users" in tables and "alembic_version" not in tables:
            # Created by a version of FitAI that predates migrations.
            if not _matches_baseline(conn):
                raise OutdatedDatabaseError(
                    "This database was created by an early FitAI version and can't be upgraded "
                    "automatically. Delete it (e.g. backend/fitai.db) and restart to create a fresh one."
                )
            command.stamp(config, BASELINE_REVISION)
        command.upgrade(config, "head")
