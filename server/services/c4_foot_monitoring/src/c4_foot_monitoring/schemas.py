"""Pydantic request/response schemas for C4.

These are the proposed fields of the ``foot_analysis`` contract. They become a contract in
``contracts/foot_analysis/`` once the team agrees them.

Patient-facing rule: the response carries no model confidence or score.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DISCLAIMER = (
    "Research prototype. This is an estimate from a photo, not a diagnosis. "
    "Always ask a doctor or nurse about any change in your feet."
)

RiskBand = Literal["Low", "Medium", "High"]


class FootAnalysisMeta(BaseModel):
    """Which model produced the result."""

    model_config = ConfigDict(frozen=True, protected_namespaces=())

    is_mock: bool = Field(description="True when the result is synthetic (no trained model).")
    model_name: str
    model_version: str


class FootAnalysisResponse(BaseModel):
    """Result of one foot photo analysis."""

    model_config = ConfigDict(extra="forbid")

    analysis_id: str = Field(description="UUID of this analysis.")
    classification: Literal["normal", "ulcer"] = Field(description="Estimated class of the photo.")
    risk_band: RiskBand = Field(description="Estimated risk band shown to the patient.")
    recommendations: list[str]
    disclaimer: str
    meta: FootAnalysisMeta


class ErrorDetail(BaseModel):
    field: str | None = None
    issue: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = []


class ErrorResponse(BaseModel):
    """The error envelope (documented for OpenAPI)."""

    error: ErrorBody
    request_id: str | None = None
