from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

COMPONENT_ROOT = Path(__file__).resolve().parents[2]


def make_config(database_url: str) -> Config:
    config = Config(str(COMPONENT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["configure_logger"] = False
    return config


def test_upgrade_and_downgrade(tmp_path: Path) -> None:
    url = f"sqlite:///{(tmp_path / 'migrations.db').as_posix()}"
    config = make_config(url)

    command.upgrade(config, "head")
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert {"nutrition_source", "food", "food_nutrient", "meal", "meal_item"} <= tables

        command.downgrade(config, "base")
        assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    finally:
        engine.dispose()


def test_patient_id_migration_assigns_existing_meals_to_the_demo_patient(tmp_path: Path) -> None:
    import uuid

    from sqlalchemy import text

    url = f"sqlite:///{(tmp_path / 'patient.db').as_posix()}"
    config = make_config(url)
    command.upgrade(config, "c3e5a1b7d2f4")

    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO meal (id, eaten_at, meal_type, note, created_at) "
                    "VALUES (1, '2026-10-16 06:00:00', NULL, NULL, '2026-10-16 06:00:00')"
                )
            )

        command.upgrade(config, "head")

        columns = {c["name"]: c for c in inspect(engine).get_columns("meal")}
        assert columns["patient_id"]["nullable"] is False
        index_names = {i["name"] for i in inspect(engine).get_indexes("meal")}
        assert "ix_meal_patient_eaten" in index_names
        with engine.connect() as connection:
            patient = connection.execute(text("SELECT patient_id FROM meal WHERE id = 1")).scalar()
        assert uuid.UUID(str(patient)) == uuid.UUID("00000000-0000-4000-8000-000000000001")

        command.downgrade(config, "c3e5a1b7d2f4")
        assert "patient_id" not in {c["name"] for c in inspect(engine).get_columns("meal")}
    finally:
        engine.dispose()
