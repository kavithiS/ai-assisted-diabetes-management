"""C3 Multi-Factor Diabetic Risk Profiling & XAI service (port 8003). Scaffold only."""

from fastapi import FastAPI

from c3_risk_xai.api.routes import router
from diacare_shared.config import BaseServiceSettings
from diacare_shared.errors import install_exception_handlers
from diacare_shared.health import create_health_router
from diacare_shared.logging import configure_logging
from diacare_shared.request_context import RequestContextMiddleware

SERVICE_NAME = "c3_risk_xai"

configure_logging(BaseServiceSettings().log_level)

app = FastAPI(title="C3 Multi-Factor Diabetic Risk Profiling & XAI", version="0.1.0")
install_exception_handlers(app)
app.add_middleware(RequestContextMiddleware)
app.include_router(create_health_router(SERVICE_NAME))
app.include_router(router)
