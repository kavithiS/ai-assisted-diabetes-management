"""Schemas shared by all endpoints, including the single error envelope used for every 4xx/5xx."""

from pydantic import BaseModel, ConfigDict, Field

from c1_food_nutrition.core.errors import ErrorCode

API_VERSION = "v1"

DISCLAIMER = (
    "Research prototype (J26-IT-352). Not a diagnostic or clinically validated tool; "
    "outputs must not be used for medical decisions."
)


class ErrorDetail(BaseModel):
    """A single field-level problem."""

    model_config = ConfigDict(frozen=True)

    field: str | None = Field(default=None, description="Offending field, if applicable.")
    issue: str = Field(description="What is wrong with the field.")


class ErrorBody(BaseModel):
    """Machine-readable code plus a human-readable explanation."""

    model_config = ConfigDict(frozen=True)

    code: ErrorCode
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Envelope returned for every error response (ADR 0004)."""

    model_config = ConfigDict(frozen=True)

    error: ErrorBody
    request_id: str | None = Field(
        default=None, description="Correlation ID; also sent as the X-Request-ID header."
    )
