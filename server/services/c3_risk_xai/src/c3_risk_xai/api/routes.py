"""C3 API routes. Thin: validation by Pydantic, all work done by services/risk_service."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from c3_risk_xai.schemas import (
    DeletedRecords,
    History,
    ModelStatus,
    PatientRiskProfile,
    RiskAssessment,
)
from c3_risk_xai.services import risk_service
from c3_risk_xai.settings import C3Settings, get_settings

router = APIRouter(prefix="/v1/risk", tags=["risk"])

# Random pseudonym made by the app (hex). A header, so it never appears in access logs.
DEVICE_ID_PATTERN = r"^[0-9a-f]{16,64}$"
OptionalDevice = Annotated[
    str | None,
    Header(
        alias="X-Device-Id",
        pattern=DEVICE_ID_PATTERN,
        description="Random device pseudonym. When sent, the assessment is saved (best-effort).",
    ),
]
RequiredDevice = Annotated[
    str,
    Header(alias="X-Device-Id", pattern=DEVICE_ID_PATTERN, description="Random device pseudonym."),
]


def _storage_error(exc: risk_service.StorageUnavailableError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.post("/assess", response_model=RiskAssessment, response_model_exclude_none=True)
def assess_risk(
    profile: PatientRiskProfile,
    settings: Annotated[C3Settings, Depends(get_settings)],
    device_id: OptionalDevice = None,
    debug: Annotated[
        bool, Query(description="Researcher view; honoured only in research mode.")
    ] = False,
) -> RiskAssessment:
    """Estimated diabetes risk band with SHAP/LIME explanations. Not a diagnosis.

    Answers 200 with status `ok`, `insufficient_data` or `invalid_input`;
    503 if the model bundles are not loaded. A stopped database never fails it.
    """
    try:
        return risk_service.assess(
            profile, include_debug=debug and settings.c3_research_mode, device_id=device_id
        )
    except risk_service.ModelsNotLoadedError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc


@router.get("/history", response_model=History, response_model_exclude_none=True)
def assessment_history(
    device_id: RequiredDevice,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> History:
    """FR13: this device's past assessments, newest first (503 if the database is down)."""
    try:
        return risk_service.history(device_id, limit)
    except risk_service.StorageUnavailableError as exc:
        raise _storage_error(exc) from exc


@router.delete("/history", response_model=DeletedRecords)
def delete_history(device_id: RequiredDevice) -> DeletedRecords:
    """FR16: delete this device's records. The audit log keeps only the action and count."""
    try:
        return risk_service.delete_device_records(device_id)
    except risk_service.StorageUnavailableError as exc:
        raise _storage_error(exc) from exc


@router.get("/status", response_model=ModelStatus)
def model_status() -> ModelStatus:
    """Models loaded and database state (kept separate from the shared /health)."""
    return risk_service.model_status()
