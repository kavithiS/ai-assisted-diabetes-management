"""Request metadata and response contract for ``POST /api/v1/meals/analyze`` (ADR 0004).

IMPORTANT: the response contains internal model-confidence fields (``FoodItem.confidence``,
``Portion.confidence``) intended only for C2 (glucose forecasting) and C3 (risk profiling +
XAI). The patient-facing UI (C4) must NOT display model confidence.

TODO(c1): this is the pre-migration contract. Align it with the ``meal_nutrition`` v1 draft in
SKILL.md section 4 when C2 and C3 review it: ``items``/``analysis_id`` vs ``foods``/``meal_id``,
required ``meal_type``, ``MRI_SL_FCDB`` vs ``SL_FCDB``, portion methods, the nutrient set,
how totals treat unknown values, and the error body shape. Decoding uses OpenCV, while
SKILL.md section 5 says Pillow.
"""

import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TypedDict
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    ValidationInfo,
    field_validator,
)

from c1_food_nutrition.schemas.common import API_VERSION, DISCLAIMER
from c1_food_nutrition.schemas.nutrition import NutrientProfile, NutritionSourceRef

# --------------------------------------------------------------------------- request metadata

#: RFC 3339 profile of ISO 8601: full date, "T", time, optional fraction, mandatory offset.
_CAPTURED_AT_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)

CAPTURED_AT_DESCRIPTION = (
    "When the meal photo was taken. Timezone-aware ISO 8601 / RFC 3339 date-time with a "
    "UTC offset or 'Z' (e.g. 2026-10-03T12:30:00+05:30). Naive datetimes, date-only values "
    "and Unix timestamps are rejected, as are values further in the future than the "
    "configured clock-skew tolerance. Returned normalised to UTC."
)

REFERENCE_OBJECT_DESCRIPTION = (
    "EXPERIMENTAL. Reserved for portion calibration with a reference object (TAF). Accepted "
    "as free text and echoed back unchanged; it has no effect yet. The format is expected to "
    "change to an enum or a dimensions object before C4 integration. That will be a "
    "breaking change."
)


class MealType(StrEnum):
    """Meal occasion supplied by the client."""

    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class MetadataValidationContext(TypedDict):
    """Runtime values needed to validate metadata (passed as Pydantic validation context)."""

    now: datetime
    max_future_skew: timedelta
    reference_object_max_length: int


class MealAnalysisMetadata(BaseModel):
    """Optional metadata sent alongside the meal image.

    Validate with ``model_validate(data, context=MetadataValidationContext(...))`` to apply
    the future-skew and length rules; without a context only format rules apply.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    meal_type: MealType | None = Field(default=None, description="Meal occasion.")
    captured_at: AwareDatetime | None = Field(default=None, description=CAPTURED_AT_DESCRIPTION)
    reference_object: str | None = Field(default=None, description=REFERENCE_OBJECT_DESCRIPTION)

    @field_validator("captured_at", mode="before")
    @classmethod
    def _parse_captured_at_strictly(cls, value: object) -> object:
        """Allow only RFC 3339 strings with an explicit offset (or aware datetimes)."""
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("captured_at must be timezone-aware")
            return value
        if not isinstance(value, str):
            raise ValueError("captured_at must be an ISO 8601 date-time string")
        if not _CAPTURED_AT_PATTERN.fullmatch(value):
            raise ValueError(
                "captured_at must be an ISO 8601 date-time with a UTC offset, "
                "e.g. 2026-10-03T12:30:00+05:30 or 2026-10-03T07:00:00Z"
            )
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:  # e.g. month 13, hour 25, offset out of range
            raise ValueError(f"captured_at is not a valid date-time: {exc}") from exc

    @field_validator("captured_at")
    @classmethod
    def _normalise_and_reject_future(
        cls, value: datetime | None, info: ValidationInfo
    ) -> datetime | None:
        """Normalise to UTC and reject timestamps beyond the allowed clock skew."""
        if value is None:
            return None
        value = value.astimezone(UTC)
        context = info.context
        if isinstance(context, dict) and "now" in context:
            latest_allowed = context["now"] + context["max_future_skew"]
            if value > latest_allowed:
                raise ValueError(
                    "captured_at is in the future beyond the allowed clock skew "
                    f"({int(context['max_future_skew'].total_seconds())}s)"
                )
        return value

    @field_validator("reference_object")
    @classmethod
    def _limit_reference_object(cls, value: str | None, info: ValidationInfo) -> str | None:
        """Enforce the configured maximum length; the value itself is not modified."""
        context = info.context
        if value is not None and isinstance(context, dict):
            max_length = context.get("reference_object_max_length")
            if max_length is not None and len(value) > max_length:
                raise ValueError(f"reference_object must be at most {max_length} characters")
        return value


# --------------------------------------------------------------------------- response

INTERNAL_CONFIDENCE_NOTE = (
    "INTERNAL, for C2/C3 only. The patient-facing UI must not display model confidence."
)


class PortionEstimationMethod(StrEnum):
    """How a portion size was obtained."""

    MOCK = "mock"
    REFERENCE_OBJECT = "reference_object"
    MODEL = "model"


class BoundingBox(BaseModel):
    """Image region of a recognised item, in coordinates normalised to [0, 1]."""

    model_config = ConfigDict(frozen=True)

    x: float = Field(ge=0, le=1, description="Left edge.")
    y: float = Field(ge=0, le=1, description="Top edge.")
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)


class Portion(BaseModel):
    """Estimated portion of one food item."""

    model_config = ConfigDict(frozen=True)

    grams: PositiveFloat = Field(description="Estimated edible mass in grams.")
    household_measure: str | None = Field(
        default=None, description="Human-friendly measure, e.g. '1 cup'."
    )
    estimation_method: PortionEstimationMethod
    # INTERNAL: consumed by C2/C3 only. Patient-facing UI must not display model confidence.
    confidence: float | None = Field(default=None, ge=0, le=1, description=INTERNAL_CONFIDENCE_NOTE)


class FoodItem(BaseModel):
    """One recognised food in the meal (a mixed dish yields several items)."""

    model_config = ConfigDict(frozen=True)

    item_id: str = Field(description="Identifier of the item within this analysis.")
    label: str = Field(description="Recognised food class label.")
    food_code: str | None = Field(
        default=None, description="Key into the food-composition tables, if matched."
    )
    # INTERNAL: consumed by C2/C3 only. Patient-facing UI must not display model confidence.
    confidence: float = Field(ge=0, le=1, description=INTERNAL_CONFIDENCE_NOTE)
    region: BoundingBox | None = None
    portion: Portion
    nutrition: NutrientProfile = Field(description="Nutrients for the estimated portion.")
    nutrition_source: NutritionSourceRef | None = None


class ImageInfo(BaseModel):
    """Properties of the accepted image, as detected by the service."""

    model_config = ConfigDict(frozen=True)

    media_type: str = Field(description="Type detected from file content, not the header.")
    width: PositiveInt
    height: PositiveInt
    size_bytes: NonNegativeInt


class AnalysisMeta(BaseModel):
    """Provenance of an analysis result."""

    model_config = ConfigDict(frozen=True)

    is_mock: bool = Field(
        description="True when any pipeline stage is a mock. Mock values are synthetic "
        "placeholders, not real recognition or nutrition data."
    )
    api_version: str = API_VERSION
    model_name: str
    model_version: str
    generated_at: AwareDatetime
    request_id: str | None = None
    warnings: list[str] = Field(default_factory=list)


class MealAnalysisResponse(BaseModel):
    """Structured dietary analysis of one meal image."""

    model_config = ConfigDict(frozen=True)

    analysis_id: UUID
    meta: AnalysisMeta
    metadata: MealAnalysisMetadata = Field(description="Validated request metadata (UTC).")
    image: ImageInfo
    items: list[FoodItem]
    totals: NutrientProfile = Field(
        description="Sum over items; a nutrient is null if it is unknown for any item."
    )
    disclaimer: str = DISCLAIMER
