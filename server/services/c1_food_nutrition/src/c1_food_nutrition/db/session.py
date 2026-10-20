"""Engine and session factory construction."""

from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from c1_food_nutrition.config import Settings


def create_db_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Create an engine for PostgreSQL (``postgresql+psycopg://``) or SQLite."""
    options: dict[str, Any] = {"echo": echo, "pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        # FastAPI runs sync endpoints in worker threads; SQLite must allow that.
        options["connect_args"] = {"check_same_thread": False}
        if database_url in ("sqlite://", "sqlite:///:memory:"):
            options["poolclass"] = StaticPool  # one shared in-memory database (tests)
    return create_engine(database_url, **options)


def engine_from_settings(settings: Settings) -> Engine:
    """Create an engine from application settings."""
    return create_db_engine(settings.database_url)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to ``engine``."""
    return sessionmaker(bind=engine, expire_on_commit=False)
