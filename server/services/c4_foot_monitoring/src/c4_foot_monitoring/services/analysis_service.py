"""Foot photo analysis: validate → classify → risk band → recommendations."""

import logging
import uuid

from starlette.concurrency import run_in_threadpool

from c4_foot_monitoring.ml.interfaces import FootClassifier
from c4_foot_monitoring.ml.risk import risk_band_for
from c4_foot_monitoring.schemas import (
    DISCLAIMER,
    FootAnalysisMeta,
    FootAnalysisResponse,
    RiskBand,
)
from c4_foot_monitoring.services.image_validation import AsyncReadable, ImageValidator

logger = logging.getLogger(__name__)

#: Placeholder wording, general foot-care advice only. To be replaced by clinician-reviewed
#: templates before any patient use [INFORMATION REQUIRED].
RECOMMENDATIONS: dict[RiskBand, list[str]] = {
    "Low": [
        "Keep checking both feet every day.",
        "Keep your feet clean and dry, and wear shoes that fit well.",
        "Show your feet to your doctor at your regular check-ups.",
    ],
    "Medium": [
        "Some areas may need a closer look. Show this foot to your doctor or nurse soon.",
        "Check this area again tomorrow and note any change.",
        "Avoid walking barefoot.",
    ],
    "High": [
        "Contact your doctor or clinic soon to have this foot checked.",
        "Do not try to treat a wound on your own.",
        "Keep pressure off the area and keep it clean and covered.",
    ],
}


class FootAnalysisService:
    """Analyses one foot photo. The photo is never stored."""

    def __init__(
        self,
        classifier: FootClassifier,
        validator: ImageValidator,
        low_risk_min_normal_probability: float,
    ) -> None:
        self._classifier = classifier
        self._validator = validator
        self._low_risk_min = low_risk_min_normal_probability

    async def analyze(
        self, image: AsyncReadable, declared_content_type: str | None
    ) -> FootAnalysisResponse:
        pixels = await self._validator.validate(image, declared_content_type)
        result = await run_in_threadpool(self._classifier.classify, pixels)
        band = risk_band_for(result, self._low_risk_min)
        analysis_id = str(uuid.uuid4())
        # Never log the image or the score.
        logger.info("Foot analysis %s done (band %s)", analysis_id, band)
        return FootAnalysisResponse(
            analysis_id=analysis_id,
            classification=result.label,
            risk_band=band,
            recommendations=list(RECOMMENDATIONS[band]),
            disclaimer=DISCLAIMER,
            meta=FootAnalysisMeta(
                is_mock=self._classifier.is_mock,
                model_name=self._classifier.model_name,
                model_version=self._classifier.model_version,
            ),
        )
