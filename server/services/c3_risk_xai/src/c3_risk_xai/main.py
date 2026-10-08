"""C3 Multi-Factor Diabetic Risk Profiling & XAI service (port 8003). Scaffold only."""

from fastapi import FastAPI

from c3_risk_xai.api.routes import router
from diacare_shared.config import BaseServiceSettings
from diacare_shared.health import create_health_router
from diacare_shared.logging import configure_logging

SERVICE_NAME = "c3_risk_xai"

configure_logging(BaseServiceSettings().log_level)

app = FastAPI(title="C3 Multi-Factor Diabetic Risk Profiling & XAI", version="0.1.0")
app.include_router(create_health_router(SERVICE_NAME))
app.include_router(router)
