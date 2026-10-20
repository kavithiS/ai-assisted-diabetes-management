"""C4 Mobile Platform & Foot Monitoring service (port 8004).

Run locally with::

    uv run uvicorn c4_foot_monitoring.main:app --port 8004 --reload
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from c4_foot_monitoring.api.routes import router
from c4_foot_monitoring.config import Settings, get_settings
from c4_foot_monitoring.core.errors import register_exception_handlers
from c4_foot_monitoring.ml.classifier import build_classifier
from c4_foot_monitoring.ml.mock import MockFootClassifier
from c4_foot_monitoring.schemas import DISCLAIMER
from diacare_shared.health import create_health_router
from diacare_shared.logging import configure_logging

SERVICE_NAME = "c4_foot_monitoring"
logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load the classifier once at startup (the trained model, or the mock)."""
    settings: Settings = app.state.settings
    app.state.classifier = await run_in_threadpool(build_classifier, settings)
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the C4 API application.

    Args:
        settings: Explicit settings (used by tests); defaults to environment-based settings.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="C4 Mobile Platform & Foot Monitoring",
        version="0.2.0",
        description=DISCLAIMER,
        lifespan=_lifespan,
    )
    app.state.settings = settings
    # Replaced at startup; set here so the app also works without running the lifespan.
    app.state.classifier = MockFootClassifier()

    register_exception_handlers(app)
    app.include_router(create_health_router(SERVICE_NAME))
    app.include_router(router)
    return app


app = create_app()
