"""Meal analysis endpoint (routes only; logic lives in services)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, UploadFile

from c1_food_nutrition.api.deps import (
    get_meal_analysis_service,
    parse_meal_metadata,
    require_multipart_form,
)
from c1_food_nutrition.schemas.common import ErrorResponse
from c1_food_nutrition.schemas.meal_analysis import MealAnalysisMetadata, MealAnalysisResponse
from c1_food_nutrition.services.pipeline import MealAnalysisService

router = APIRouter(prefix="/v1/meals", tags=["meals"])

_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Malformed multipart body."},
    413: {"model": ErrorResponse, "description": "IMAGE_TOO_LARGE."},
    415: {
        "model": ErrorResponse,
        "description": "UNSUPPORTED_MEDIA_TYPE: not multipart, or image is not an allowed type.",
    },
    422: {
        "model": ErrorResponse,
        "description": "IMAGE_REQUIRED, IMAGE_UNREADABLE or INVALID_METADATA.",
    },
}


@router.post(
    "/analyze",
    summary="Analyse a meal image (Phase 0: returns a MOCK response)",
    responses=_ERROR_RESPONSES,
    dependencies=[Depends(require_multipart_form)],
)
async def analyze_meal(
    image: Annotated[
        UploadFile,
        File(description="Meal photo. JPEG or PNG; allowed types and max size are set by config."),
    ],
    metadata: Annotated[MealAnalysisMetadata, Depends(parse_meal_metadata)],
    service: Annotated[MealAnalysisService, Depends(get_meal_analysis_service)],
) -> MealAnalysisResponse:
    """Recognise foods, estimate portions and compute nutrition for one meal image.

    Phase 0: the pipeline uses mock components; ``meta.is_mock`` is ``true`` and all
    items and nutrient values are synthetic placeholders.

    Confidence fields in the response are INTERNAL (for C2/C3). The patient-facing UI
    must not display model confidence.
    """
    return await service.analyze(
        image=image, declared_content_type=image.content_type, metadata=metadata
    )
