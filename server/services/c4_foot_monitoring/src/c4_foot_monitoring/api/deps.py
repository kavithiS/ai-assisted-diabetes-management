"""FastAPI dependencies for C4."""

from typing import Annotated

from fastapi import Depends, Request

from c4_foot_monitoring.config import Settings
from c4_foot_monitoring.core.errors import ErrorDetailItem, UnsupportedMediaTypeError
from c4_foot_monitoring.ml.interfaces import FootClassifier
from c4_foot_monitoring.services.analysis_service import FootAnalysisService
from c4_foot_monitoring.services.image_validation import ImageValidator


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_classifier(request: Request) -> FootClassifier:
    classifier: FootClassifier = request.app.state.classifier
    return classifier


def get_analysis_service(
    settings: Annotated[Settings, Depends(get_app_settings)],
    classifier: Annotated[FootClassifier, Depends(get_classifier)],
) -> FootAnalysisService:
    return FootAnalysisService(
        classifier=classifier,
        validator=ImageValidator.from_settings(settings),
        low_risk_min_normal_probability=settings.foot_low_risk_min_normal_probability,
    )


def require_multipart_form(request: Request) -> None:
    """Reject bodies that are not ``multipart/form-data`` with 415."""
    content_type = request.headers.get("content-type", "").lower()
    if not content_type.startswith("multipart/form-data"):
        raise UnsupportedMediaTypeError(
            "Send the foot image as multipart/form-data.",
            [ErrorDetailItem(field="Content-Type", issue="must be multipart/form-data")],
        )
