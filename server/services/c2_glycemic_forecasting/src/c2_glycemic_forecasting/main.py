"""C2 Glycemic Prediction & Risk Forecasting service (port 8002). Scaffold only."""

from fastapi import FastAPI

from c2_glycemic_forecasting.api.routes import router
from diacare_shared.config import BaseServiceSettings
from diacare_shared.health import create_health_router
from diacare_shared.logging import configure_logging

SERVICE_NAME = "c2_glycemic_forecasting"

configure_logging(BaseServiceSettings().log_level)

app = FastAPI(title="C2 Glycemic Prediction & Risk Forecasting", version="0.1.0")
app.include_router(create_health_router(SERVICE_NAME))
app.include_router(router)
