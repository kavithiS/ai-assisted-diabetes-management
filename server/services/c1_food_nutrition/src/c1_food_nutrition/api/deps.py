"""FastAPI dependencies: settings, clock, services and request parsing."""

from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Form, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from c1_food_nutrition.config import Settings
from c1_food_nutrition.core.errors import (
    ErrorDetailItem,
    InvalidMetadataError,
    UnsupportedMediaTypeError,
)
from c1_food_nutrition.ml.interfaces import FoodRecognizer
from c1_food_nutrition.ml.mock import MockFoodRecognizer, MockPortionEstimator
from c1_food_nutrition.schemas.meal_analysis import (
    CAPTURED_AT_DESCRIPTION,
    REFERENCE_OBJECT_DESCRIPTION,
    MealAnalysisMetadata,
    MealType,
    MetadataValidationContext,
)
from c1_food_nutrition.services.image_validation import ImageValidator, normalize_media_type
from c1_food_nutrition.services.nutrition import (
    CompositionTableLookup,
    NutritionLookup,
    PlaceholderNutritionLookup,
)
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


@lru_cache(maxsize=2)
def _load_trained_recognizer(path: Path, device: str) -> FoodRecognizer:
    """Load the model bundle once per process, not once per request."""
    from c1_food_nutrition.ml.torch_recognizer import TorchFoodRecognizer

    return TorchFoodRecognizer(path, device=device)


def build_recognizer(settings: Settings) -> FoodRecognizer:
    """The recogniser selected by ``RECOGNIZER``: the mock, or the trained model."""
    if settings.recognizer == "torch" and settings.model_path is not None:
        return _load_trained_recognizer(settings.model_path, settings.model_device)
    return MockFoodRecognizer()


@lru_cache(maxsize=2)
def _load_composition_table(path: Path) -> NutritionLookup:
    """Read the composition table once per process, not once per request."""
    return CompositionTableLookup.from_csv(path)


def build_nutrition_lookup(settings: Settings) -> NutritionLookup:
    """The table in ``NUTRITION_TABLE_PATH``, or the mock lookup when it is not set."""
    if settings.nutrition_table_path is not None:
        return _load_composition_table(settings.nutrition_table_path)
    return PlaceholderNutritionLookup()


def get_meal_analysis_service(settings: SettingsDep, clock: ClockDep) -> MealAnalysisService:
    """Build the analysis service.

    Portion estimation is still MOCK, so every response is flagged ``meta.is_mock = true``.
    The recogniser is the mock unless ``RECOGNIZER=torch``, and the nutrition lookup is the
    mock unless ``NUTRITION_TABLE_PATH`` is set.
    """
    return MealAnalysisService(
        image_validator=ImageValidator.from_settings(settings),
        recognizer=build_recognizer(settings),
        portion_estimator=MockPortionEstimator(),
        nutrition_lookup=build_nutrition_lookup(settings),
        clock=clock,
    )


def get_session(request: Request) -> Iterator[Session]:
    """One database session per request; the endpoint commits what it wants to keep."""
    with request.app.state.session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


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
