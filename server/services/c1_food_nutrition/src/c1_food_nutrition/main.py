"""C1 Food Recognition & Nutritional Analysis service (port 8001).

Run locally with::

    uv run uvicorn c1_food_nutrition.main:app --port 8001 --reload
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from c1_food_nutrition import __version__
from c1_food_nutrition.api.deps import build_recognizer
from c1_food_nutrition.api.exception_handlers import register_exception_handlers
from c1_food_nutrition.api.history import router as history_router
from c1_food_nutrition.api.internal import router as internal_router
from c1_food_nutrition.api.middleware import BodySizeLimitMiddleware, RequestContextMiddleware
from c1_food_nutrition.api.routes import router
from c1_food_nutrition.config import Settings, get_settings
from c1_food_nutrition.core.logging import configure_logging
from c1_food_nutrition.db.session import create_session_factory, engine_from_settings
from c1_food_nutrition.schemas.common import DISCLAIMER
from diacare_shared.health import create_health_router

SERVICE_NAME = "c1_food_nutrition"
logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Pre-load the food recogniser at startup so the first request is not slow."""
    settings: Settings = app.state.settings
    if settings.recognizer == "torch":
        logger.info("Pre-loading food recogniser at startup")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, build_recognizer, settings)
        logger.info("Food recogniser ready.")
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the C1 API application.

    Args:
        settings: Explicit settings (used by tests); defaults to environment-based settings.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="C1 Food Recognition & Nutritional Analysis",
        version=__version__,
        description=DISCLAIMER,
        lifespan=_lifespan,
    )
    app.state.settings = settings
    # Creating the engine does not connect; the first history request does.
    app.state.engine = engine_from_settings(settings)
    app.state.session_factory = create_session_factory(app.state.engine)

    register_exception_handlers(app)
    # Middleware added last runs first: RequestContext wraps everything.
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=settings.max_request_bytes)
    app.add_middleware(RequestContextMiddleware)

    app.include_router(create_health_router(SERVICE_NAME))
    app.include_router(router)
    app.include_router(history_router)
    app.include_router(internal_router)
    return app


app = create_app()
