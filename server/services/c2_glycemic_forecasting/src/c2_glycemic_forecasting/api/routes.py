"""C2 API routes for glucose forecasting."""

import logging
import zipfile

from fastapi import APIRouter, HTTPException, status

from c2_glycemic_forecasting.model import predict_glucose
from c2_glycemic_forecasting.schemas import (
    GlucoseForecastRequest,
    GlucoseForecastResponse,
)

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/glucose", tags=["glucose"])

HORIZON_MINUTES = list(range(15, 241, 15))
MODEL_NAME = "GRU"
MODEL_VERSION = "gru-single-step-premeal-fix-seed42-049cb23b"
DISCLAIMER = (
    "This forecast is a research prediction, not a medical diagnosis "
    "or a substitute for professional medical advice."
)


@router.post(
    "/forecast",
    response_model=GlucoseForecastResponse,
    status_code=status.HTTP_200_OK,
)
def forecast_glucose(
    request: GlucoseForecastRequest,
) -> GlucoseForecastResponse:
    """Predict glucose at 15-minute intervals over the next four hours."""
    features = [
        request.premeal_glucose,
        request.calories,
        request.carbs,
        request.protein,
        request.fat,
        request.fiber,
    ]

    try:
        predictions = predict_glucose(features)
    except (RecursionError, NotImplementedError):
        # RuntimeError subclasses that signal programming errors stay unhandled (500).
        raise
    except (FileNotFoundError, OSError, ValueError, zipfile.BadZipFile, RuntimeError) as error:
        # Never log `request` or `features`: they hold patient glucose and nutrition values.
        LOGGER.error("C2 model prediction failed (%s).", type(error).__name__, exc_info=error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The C2 forecasting model is currently unavailable.",
        ) from error

    return GlucoseForecastResponse(
        predictions=predictions,
        horizon_minutes=HORIZON_MINUTES,
        unit="mg/dL",
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        disclaimer=DISCLAIMER,
    )
