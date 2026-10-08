"""C1 Food Recognition & Nutritional Analysis service (port 8001).

Run locally with::

    uv run uvicorn c1_food_nutrition.main:app --port 8001 --reload
"""

from fastapi import FastAPI

from c1_food_nutrition import __version__
from c1_food_nutrition.api.exception_handlers import register_exception_handlers
from c1_food_nutrition.api.middleware import BodySizeLimitMiddleware, RequestContextMiddleware
from c1_food_nutrition.api.routes import router
from c1_food_nutrition.config import Settings, get_settings
from c1_food_nutrition.core.logging import configure_logging
from c1_food_nutrition.schemas.common import DISCLAIMER
from diacare_shared.health import create_health_router

SERVICE_NAME = "c1_food_nutrition"


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
    )
    app.state.settings = settings

    register_exception_handlers(app)
    # Middleware added last runs first: RequestContext wraps everything.
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=settings.max_request_bytes)
    app.add_middleware(RequestContextMiddleware)

    app.include_router(create_health_router(SERVICE_NAME))
    app.include_router(router)
    return app


app = create_app()
