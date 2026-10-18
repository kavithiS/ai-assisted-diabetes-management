"""Engine and session factory for a service that owns one schema."""

from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def make_engine(url: str, schema: str | None = None, *, echo: bool = False) -> Engine:
    """PostgreSQL (``postgresql+psycopg://``) or SQLite engine.

    PostgreSQL gets small pools so five packages stay well below its 100-connection default.
    SQLite has no schemas, so ``schema`` is mapped to "no schema" there (unit tests).
    """
    options: dict[str, Any] = {"echo": echo, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            options["poolclass"] = StaticPool
        if schema:
            options["execution_options"] = {"schema_translate_map": {schema: None}}
    else:
        options["pool_size"] = 5
        options["max_overflow"] = 5
    return create_engine(url, **options)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """A session factory bound to ``engine``."""
    return sessionmaker(bind=engine, expire_on_commit=False)
