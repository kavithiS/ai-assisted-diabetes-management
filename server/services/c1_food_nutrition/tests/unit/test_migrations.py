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
        assert {"nutrition_source", "food", "food_nutrient"} <= tables

        command.downgrade(config, "base")
        assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    finally:
        engine.dispose()
