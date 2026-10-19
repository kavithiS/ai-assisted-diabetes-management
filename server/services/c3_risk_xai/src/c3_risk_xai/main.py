"""C3 Multi-Factor Diabetic Risk Profiling & XAI service (port 8003)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from c3_risk_xai.api.routes import router
from c3_risk_xai.services import risk_service
from c3_risk_xai.settings import get_settings
from diacare_shared.config import BaseServiceSettings
from diacare_shared.health import create_health_router
from diacare_shared.logging import configure_logging

SERVICE_NAME = "c3_risk_xai"

configure_logging(BaseServiceSettings().log_level)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Load the model bundles once. If they are missing the service still starts:
    # /health stays ok, /v1/risk/status reports model_loaded false, assess answers 503.
    risk_service.load_models()
    # Same for the database: if it is down the service still answers (saving is best-effort).
    settings = get_settings()
    risk_service.init_storage(settings.c3_persistence, settings.database_url)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="C3 Multi-Factor Diabetic Risk Profiling & XAI",
        version="0.2.0",
        lifespan=lifespan,
    )
    app.include_router(create_health_router(SERVICE_NAME))
    app.include_router(router)
    return app


app = create_app()
