"""Alembic environment for C3: schema `c3` only, with its own version table there."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import text

from c3_risk_xai.db.models import SCHEMA, Base
from c3_risk_xai.db.repository import make_engine
from c3_risk_xai.settings import C3Settings

target_metadata = Base.metadata
if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)


def run_migrations_online() -> None:
    # DATABASE_URL from the environment / .env (never printed or logged).
    engine = make_engine(C3Settings().database_url)
    with engine.connect() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="alembic_version",
            version_table_schema=SCHEMA,
            include_schemas=True,
            include_name=lambda name, type_, _parent: type_ != "schema" or name == SCHEMA,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
