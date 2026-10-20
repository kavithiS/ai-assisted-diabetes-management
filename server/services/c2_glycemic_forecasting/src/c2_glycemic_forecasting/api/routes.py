"""C2 API routes for glucose forecasting and the post-meal response indicator."""

import logging
import zipfile
from dataclasses import asdict

import xgboost as xgb
from fastapi import APIRouter, HTTPException, status

from c2_glycemic_forecasting import dietary_risk
from c2_glycemic_forecasting.model import predict_glucose
from c2_glycemic_forecasting.schemas import (
    DietaryRiskRequest,
    DietaryRiskResponse,
    GlucoseForecastRequest,
    GlucoseForecastResponse,
    ResponseIndicator,
    TrajectoryFeaturesResponse,
)
from c2_glycemic_forecasting.trajectory_features import (
    build_feature_row,
    extract_trajectory_features,
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
INDICATOR_DEFINITION = (
    "Estimates whether at least one CGM reading from 15 to 240 minutes after the meal will be "
    "above 180 mg/dL. Research-defined post-meal hyperglycaemic response indicator; not a "
    "diagnosis or a clinically validated risk category."
)
DIETARY_RISK_DISCLAIMER = (
    "These are research estimates, not a medical diagnosis, a clinically validated risk "
    "category or a substitute for professional medical advice."
)


def _predict_trajectory(request: GlucoseForecastRequest) -> list[float]:
    """Run the GRU. Model failures become 503; patient values are never logged."""
    features = [
        request.premeal_glucose,
        request.calories,
        request.carbs,
        request.protein,
        request.fat,
        request.fiber,
    ]

    try:
        return predict_glucose(features)
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


@router.post(
    "/forecast",
    response_model=GlucoseForecastResponse,
    status_code=status.HTTP_200_OK,
)
def forecast_glucose(
    request: GlucoseForecastRequest,
) -> GlucoseForecastResponse:
    """Predict glucose at 15-minute intervals over the next four hours."""
    predictions = _predict_trajectory(request)

    return GlucoseForecastResponse(
        predictions=predictions,
        horizon_minutes=HORIZON_MINUTES,
        unit="mg/dL",
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        disclaimer=DISCLAIMER,
    )


def _estimate_indicator(request: DietaryRiskRequest, predictions: list[float]) -> ResponseIndicator:
    """Classify the meal, or report the indicator as unavailable. Never invents a value."""
    unavailable = ResponseIndicator(
        status="unavailable",
        estimated_above_180=None,
        definition=INDICATOR_DEFINITION,
        evaluation_note=None,
        model_name=None,
        model_version=None,
    )
    try:
        classifier = dietary_risk.load_classifier()
        features = build_feature_row(
            request.premeal_glucose,
            request.calories,
            request.carbs,
            request.protein,
            request.fat,
            request.fiber,
            predictions,
        )
        estimate = classifier.estimate_above_threshold(features)
    except (dietary_risk.ClassifierUnavailableError, ValueError, xgb.core.XGBoostError) as error:
        LOGGER.error(
            "C2 dietary-risk classifier failed (%s).", type(error).__name__, exc_info=error
        )
        return unavailable

    return ResponseIndicator(
        status="available",
        estimated_above_180=estimate,
        definition=INDICATOR_DEFINITION,
        evaluation_note=classifier.evaluation_note,
        model_name=classifier.model_name,
        model_version=classifier.model_version,
    )


@router.post(
    "/dietary-risk",
    response_model=DietaryRiskResponse,
    status_code=status.HTTP_200_OK,
)
def assess_dietary_risk(request: DietaryRiskRequest) -> DietaryRiskResponse:
    """Forecast the meal's glucose response, summarise it and estimate the response indicator."""
    predictions = _predict_trajectory(request)
    try:
        trajectory = extract_trajectory_features(request.premeal_glucose, predictions)
    except ValueError as error:
        LOGGER.error("C2 trajectory features failed (%s).", type(error).__name__, exc_info=error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The C2 forecasting model is currently unavailable.",
        ) from error

    return DietaryRiskResponse(
        predictions=predictions,
        horizon_minutes=HORIZON_MINUTES,
        unit="mg/dL",
        trajectory_features=TrajectoryFeaturesResponse(**asdict(trajectory)),
        response_indicator=_estimate_indicator(request, predictions),
        forecast_model_name=MODEL_NAME,
        forecast_model_version=MODEL_VERSION,
        disclaimer=DIETARY_RISK_DISCLAIMER,
    )
