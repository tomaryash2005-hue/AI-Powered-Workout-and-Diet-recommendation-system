from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, inspect, text

from app.database import Base
from app.migrate import OutdatedDatabaseError, alembic_config, migrate


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    return create_engine(f"sqlite:///{tmp_path / 'test.db'}")


def head_revision() -> str:
    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def current_revision(engine: Engine) -> str | None:
    with engine.connect() as conn:
        return MigrationContext.configure(conn).get_current_revision()


def test_migrations_match_models(engine: Engine) -> None:
    migrate(engine)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == [], "Models changed without a migration — run `alembic revision --autogenerate`"
    assert current_revision(engine) == head_revision()


def test_migrate_is_idempotent(engine: Engine) -> None:
    migrate(engine)
    migrate(engine)
    assert current_revision(engine) == head_revision()


def test_downgrade_to_base_and_back(engine: Engine) -> None:
    migrate(engine)
    with engine.begin() as conn:
        command.downgrade(alembic_config(conn), "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    migrate(engine)
    assert "profiles" in inspect(engine).get_table_names()


def test_database_created_before_migrations_is_adopted(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO users (email, name, hashed_password, created_at) VALUES ('a@b.c', 'A', 'x', '2026-01-01')")
        )
    migrate(engine)
    assert current_revision(engine) == head_revision()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM users")).scalar() == 1


def test_early_database_without_new_columns_is_rejected(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE profiles (user_id INTEGER PRIMARY KEY, age INTEGER)"))
    with pytest.raises(OutdatedDatabaseError):
        migrate(engine)
