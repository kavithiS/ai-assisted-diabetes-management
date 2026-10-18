"""C4 Mobile Platform & Foot Monitoring service (port 8004). Scaffold only."""

from fastapi import FastAPI

from c4_foot_monitoring.api.routes import router
from diacare_shared.config import BaseServiceSettings
from diacare_shared.errors import install_exception_handlers
from diacare_shared.health import create_health_router
from diacare_shared.logging import configure_logging
from diacare_shared.request_context import RequestContextMiddleware

SERVICE_NAME = "c4_foot_monitoring"

configure_logging(BaseServiceSettings().log_level)

app = FastAPI(title="C4 Mobile Platform & Foot Monitoring", version="0.1.0")
install_exception_handlers(app)
app.add_middleware(RequestContextMiddleware)
app.include_router(create_health_router(SERVICE_NAME))
app.include_router(router)
