"""C2 Glycemic Prediction & Risk Forecasting service (port 8002). Scaffold only."""

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from c2_glycemic_forecasting.api.routes import router
from diacare_shared.config import BaseServiceSettings
from diacare_shared.health import create_health_router
from diacare_shared.logging import configure_logging

SERVICE_NAME = "c2_glycemic_forecasting"

configure_logging(BaseServiceSettings().log_level)

app = FastAPI(title="C2 Glycemic Prediction & Risk Forecasting", version="0.1.0")
app.include_router(create_health_router(SERVICE_NAME))
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return 422 without echoing rejected input, which may be NaN and not JSON-safe."""
    errors = [
        {key: value for key, value in error.items() if key != "input"} for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})
