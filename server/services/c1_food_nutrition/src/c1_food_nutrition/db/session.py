"""Engine and session factory construction."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from c1_food_nutrition.config import Settings


def create_db_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Create an engine for PostgreSQL (``postgresql+psycopg://``) or SQLite."""
    return create_engine(database_url, echo=echo, pool_pre_ping=True)


def engine_from_settings(settings: Settings) -> Engine:
    """Create an engine from application settings."""
    return create_db_engine(settings.database_url)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to ``engine``."""
    return sessionmaker(bind=engine, expire_on_commit=False)
