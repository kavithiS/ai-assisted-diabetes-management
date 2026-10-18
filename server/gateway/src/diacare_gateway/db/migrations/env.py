"""Alembic environment: uses GATEWAY_DATABASE_URL from the gateway settings."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

import diacare_gateway.db.models  # noqa: F401  (registers tables on Base.metadata)
from diacare_gateway.config import GatewaySettings
from diacare_gateway.db.base import CORE_SCHEMA, Base

config = context.config

if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# An explicitly provided URL (e.g. from tests) wins over the environment.
if not config.get_main_option("sqlalchemy.url"):
    url = GatewaySettings().gateway_database_url
    if not url:
        raise RuntimeError("GATEWAY_DATABASE_URL is not set")
    config.set_main_option("sqlalchemy.url", url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a database connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=CORE_SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        on_postgres = connection.dialect.name == "postgresql"
        if on_postgres:
            # The version table lives in the schema, so the schema must exist first.
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {CORE_SCHEMA}"))
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=CORE_SCHEMA if on_postgres else None,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
