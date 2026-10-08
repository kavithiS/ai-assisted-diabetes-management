"""FastAPI dependencies: settings, clock, services and request parsing."""

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, Form, Request
from pydantic import ValidationError

from c1_food_nutrition.config import Settings
from c1_food_nutrition.core.errors import (
    ErrorDetailItem,
    InvalidMetadataError,
    UnsupportedMediaTypeError,
)
from c1_food_nutrition.ml.mock import MockFoodRecognizer, MockPortionEstimator
from c1_food_nutrition.schemas.meal_analysis import (
    CAPTURED_AT_DESCRIPTION,
    REFERENCE_OBJECT_DESCRIPTION,
    MealAnalysisMetadata,
    MealType,
    MetadataValidationContext,
)
from c1_food_nutrition.services.image_validation import ImageValidator, normalize_media_type
from c1_food_nutrition.services.nutrition import PlaceholderNutritionLookup
from c1_food_nutrition.services.pipeline import MealAnalysisService, utc_now


def get_app_settings(request: Request) -> Settings:
    """Return the settings the application was created with."""
    settings: Settings = request.app.state.settings
    return settings


def get_clock() -> Callable[[], datetime]:
    """Return the clock used for time-dependent validation (overridable in tests)."""
    return utc_now


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
ClockDep = Annotated[Callable[[], datetime], Depends(get_clock)]


def get_meal_analysis_service(settings: SettingsDep, clock: ClockDep) -> MealAnalysisService:
    """Build the analysis service.

    Phase 0 wires MOCK recogniser, portion estimator and nutrition lookup; responses are
    therefore flagged ``meta.is_mock = true``.
    """
    return MealAnalysisService(
        image_validator=ImageValidator.from_settings(settings),
        recognizer=MockFoodRecognizer(),
        portion_estimator=MockPortionEstimator(),
        nutrition_lookup=PlaceholderNutritionLookup(),
        clock=clock,
    )


def require_multipart_form(request: Request) -> None:
    """Reject requests that are not ``multipart/form-data`` with 415."""
    content_type = request.headers.get("content-type")
    if normalize_media_type(content_type) != "multipart/form-data":
        raise UnsupportedMediaTypeError(
            "Request body must be multipart/form-data.",
            [ErrorDetailItem(field=None, issue=f"got Content-Type {content_type!r}")],
        )


def parse_meal_metadata(
    settings: SettingsDep,
    clock: ClockDep,
    meal_type: Annotated[
        str | None,
        Form(
            description="Meal occasion.",
            json_schema_extra={"enum": [m.value for m in MealType]},
        ),
    ] = None,
    captured_at: Annotated[
        str | None,
        Form(description=CAPTURED_AT_DESCRIPTION, json_schema_extra={"format": "date-time"}),
    ] = None,
    reference_object: Annotated[
        str | None,
        Form(
            description=REFERENCE_OBJECT_DESCRIPTION,
            json_schema_extra={"x-experimental": True},
        ),
    ] = None,
) -> MealAnalysisMetadata:
    """Validate the optional metadata form fields strictly (ADR 0004)."""
    context = MetadataValidationContext(
        now=clock(),
        max_future_skew=timedelta(seconds=settings.captured_at_max_future_skew_seconds),
        reference_object_max_length=settings.reference_object_max_length,
    )
    try:
        return MealAnalysisMetadata.model_validate(
            {
                "meal_type": meal_type,
                "captured_at": captured_at,
                "reference_object": reference_object,
            },
            context=context,
        )
    except ValidationError as exc:
        raise InvalidMetadataError(
            "One or more metadata fields are invalid.",
            [
                ErrorDetailItem(
                    field=".".join(str(part) for part in err["loc"]) or None,
                    issue=err["msg"].removeprefix("Value error, "),
                )
                for err in exc.errors()
            ],
        ) from exc
