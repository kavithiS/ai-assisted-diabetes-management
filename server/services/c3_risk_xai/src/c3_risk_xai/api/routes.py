"""C3 API routes. Thin: validation by Pydantic, all work done by services/risk_service."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from c3_risk_xai.schemas import ModelStatus, PatientRiskProfile, RiskAssessment
from c3_risk_xai.services import risk_service
from c3_risk_xai.settings import C3Settings, get_settings

router = APIRouter(prefix="/v1/risk", tags=["risk"])


@router.post("/assess", response_model=RiskAssessment, response_model_exclude_none=True)
def assess_risk(
    profile: PatientRiskProfile,
    settings: Annotated[C3Settings, Depends(get_settings)],
    debug: Annotated[
        bool, Query(description="Researcher view; honoured only in research mode.")
    ] = False,
) -> RiskAssessment:
    """Estimated diabetes risk band with SHAP/LIME explanations. Not a diagnosis.

    Answers 200 with status `ok`, `insufficient_data` or `invalid_input`;
    503 if the model bundles are not loaded.
    """
    try:
        return risk_service.assess(profile, include_debug=debug and settings.c3_research_mode)
    except risk_service.ModelsNotLoadedError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc


@router.get("/status", response_model=ModelStatus)
def model_status() -> ModelStatus:
    """Whether the model bundles are loaded (kept separate from the shared /health)."""
    return risk_service.model_status()
