"""C4 foot analysis endpoint (routes only; logic lives in services)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, UploadFile

from c4_foot_monitoring.api.deps import get_analysis_service, require_multipart_form
from c4_foot_monitoring.schemas import ErrorResponse, FootAnalysisResponse
from c4_foot_monitoring.services.analysis_service import FootAnalysisService

router = APIRouter(prefix="/v1/foot", tags=["foot"])

_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    413: {"model": ErrorResponse, "description": "IMAGE_TOO_LARGE."},
    415: {
        "model": ErrorResponse,
        "description": "UNSUPPORTED_MEDIA_TYPE: not multipart, or not a JPEG/PNG image.",
    },
    422: {"model": ErrorResponse, "description": "IMAGE_REQUIRED or IMAGE_UNREADABLE."},
}


@router.post(
    "/analyze",
    response_model=FootAnalysisResponse,
    summary="Estimate foot abnormality from a photo",
    responses=_ERROR_RESPONSES,
    dependencies=[Depends(require_multipart_form)],
)
async def analyze_foot(
    image: Annotated[UploadFile, File(description="Foot photo, JPEG or PNG.")],
    service: Annotated[FootAnalysisService, Depends(get_analysis_service)],
) -> FootAnalysisResponse:
    """Estimated class and risk band for one foot photo. Not a diagnosis.

    ``meta.is_mock`` is true while no trained model is configured. The response carries no
    model confidence (patient-facing rule).
    """
    return await service.analyze(image, image.content_type)
