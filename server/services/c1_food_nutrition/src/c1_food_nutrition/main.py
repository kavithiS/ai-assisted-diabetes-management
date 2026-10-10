"""C1 Food Recognition & Nutritional Analysis service (port 8001). Scaffold only."""

from fastapi import FastAPI

from c1_food_nutrition.api.routes import router
from diacare_shared.config import BaseServiceSettings
from diacare_shared.health import create_health_router
from diacare_shared.logging import configure_logging

SERVICE_NAME = "c1_food_nutrition"

configure_logging(BaseServiceSettings().log_level)

app = FastAPI(title="C1 Food Recognition & Nutritional Analysis", version="0.1.0")
app.include_router(create_health_router(SERVICE_NAME))
app.include_router(router)
