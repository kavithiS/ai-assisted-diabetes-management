from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

GATEWAY_ROOT = Path(__file__).resolve().parents[1]
CORE_TABLES = {"app_user", "refresh_token", "consent", "audit_event"}


def make_config(database_url: str) -> Config:
    config = Config(str(GATEWAY_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["configure_logger"] = False
    return config


def test_core_tables_upgrade_and_downgrade(tmp_path: Path) -> None:
    url = f"sqlite:///{(tmp_path / 'core.db').as_posix()}"
    config = make_config(url)

    command.upgrade(config, "head")
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) >= CORE_TABLES

        # One account per e-mail address, whatever its letter case.
        insert = (
            "INSERT INTO app_user (id, email, password_hash, role, is_active, is_demo, created_at) "
            "VALUES ('{id}', '{email}', 'x', 'patient', 1, 0, '2026-10-18 00:00:00')"
        )
        with engine.begin() as connection:
            connection.exec_driver_sql(insert.format(id="1" * 32, email="A@example.test"))
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.exec_driver_sql(insert.format(id="2" * 32, email="a@EXAMPLE.test"))

        command.downgrade(config, "base")
        assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    finally:
        engine.dispose()
