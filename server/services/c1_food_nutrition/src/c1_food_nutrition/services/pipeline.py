"""Orchestrates the C1 pipeline for one meal image.

image -> validation/decoding -> recognition -> portion estimation -> composition lookup
-> nutrition calculation -> ``MealAnalysisResponse``.
"""

import asyncio
import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from uuid import uuid4

from c1_food_nutrition.core.context import get_request_id
from c1_food_nutrition.ml.interfaces import FoodRecognizer, PortionEstimator
from c1_food_nutrition.schemas.meal_analysis import (
    AnalysisMeta,
    BoundingBox,
    FoodItem,
    ImageInfo,
    MealAnalysisMetadata,
    MealAnalysisResponse,
    Portion,
    PortionEstimationMethod,
)
from c1_food_nutrition.schemas.nutrition import NutrientProfile
from c1_food_nutrition.services.image_validation import AsyncReadable, ImageValidator
from c1_food_nutrition.services.nutrition import NutritionLookup, scale_profile, sum_profiles

logger = logging.getLogger(__name__)

MOCK_WARNING = (
    "MOCK RESPONSE: food items, portions and nutrient values are synthetic placeholders, "
    "not real recognition or nutrition data."
)
NO_FOOD_WARNING = "No food was recognised in the image."
NO_NUTRITION_WARNING = (
    "No nutrition data for '{label}': its nutrients, and the meal totals, are unknown (null)."
)


def utc_now() -> datetime:
    """Return the current time in UTC (the default clock)."""
    return datetime.now(UTC)


class MealAnalysisService:
    """Runs the dietary analysis pipeline with injected components."""

    def __init__(
        self,
        *,
        image_validator: ImageValidator,
        recognizer: FoodRecognizer,
        portion_estimator: PortionEstimator,
        nutrition_lookup: NutritionLookup,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._image_validator = image_validator
        self._recognizer = recognizer
        self._portion_estimator = portion_estimator
        self._nutrition_lookup = nutrition_lookup
        self._clock = clock

    @property
    def mock_parts(self) -> list[str]:
        """Names of the pipeline stages that produce synthetic output."""
        stages = (
            ("food recognition", self._recognizer.is_mock),
            ("portion estimation", self._portion_estimator.is_mock),
            ("nutrition lookup", self._nutrition_lookup.is_mock),
        )
        return [name for name, is_mock in stages if is_mock]

    @property
    def is_mock(self) -> bool:
        """True if any pipeline stage produces synthetic output."""
        return bool(self.mock_parts)

    def _warnings(self, item_count: int, extra: Sequence[str] = ()) -> list[str]:
        """Warnings: which stages are synthetic, an empty result, then per-food notes."""
        parts = self.mock_parts
        warnings: list[str] = []
        if len(parts) == 3:
            warnings.append(MOCK_WARNING)
        elif parts:
            warnings.append(
                f"PARTLY MOCK RESPONSE: synthetic placeholders are used for {' and '.join(parts)}; "
                "they are not real data."
            )
        if item_count == 0:
            warnings.append(NO_FOOD_WARNING)
        return [*warnings, *extra]

    async def analyze(
        self,
        *,
        image: AsyncReadable,
        declared_content_type: str | None,
        metadata: MealAnalysisMetadata,
    ) -> MealAnalysisResponse:
        """Validate the image and produce the structured nutrition analysis.

        Raises:
            AppError: subclasses for invalid uploads (see ``image_validation``).
        """
        validated = await self._image_validator.validate(image, declared_content_type)
        # Recognition is synchronous and can take a while: keep it off the event loop.
        recognized = await asyncio.to_thread(self._recognizer.recognize, validated.pixels)

        items: list[FoodItem] = []
        notes: list[str] = []
        for index, food in enumerate(recognized, start=1):
            estimate = self._portion_estimator.estimate(
                validated.pixels, food, metadata.reference_object
            )
            lookup = self._nutrition_lookup.per_100g(food.food_code) if food.food_code else None
            nutrition = scale_profile(lookup[0], estimate.grams) if lookup else NutrientProfile()
            if food.match_note and food.match_note not in notes:
                notes.append(food.match_note)
            if lookup is None and not self._nutrition_lookup.is_mock:
                missing = NO_NUTRITION_WARNING.format(label=food.label)
                if missing not in notes:
                    notes.append(missing)
            items.append(
                FoodItem(
                    item_id=f"item-{index}",
                    label=food.label,
                    food_code=food.food_code,
                    confidence=food.confidence,
                    region=(
                        BoundingBox(
                            x=food.region.x,
                            y=food.region.y,
                            width=food.region.width,
                            height=food.region.height,
                        )
                        if food.region
                        else None
                    ),
                    portion=Portion(
                        grams=estimate.grams,
                        household_measure=estimate.household_measure,
                        estimation_method=PortionEstimationMethod(estimate.method),
                        confidence=estimate.confidence,
                    ),
                    nutrition=nutrition,
                    nutrition_source=lookup[1] if lookup else None,
                )
            )

        is_mock = self.is_mock
        response = MealAnalysisResponse(
            analysis_id=uuid4(),
            meta=AnalysisMeta(
                is_mock=is_mock,
                model_name=self._recognizer.model_name,
                model_version=self._recognizer.model_version,
                generated_at=self._clock(),
                request_id=get_request_id(),
                warnings=self._warnings(len(items), notes),
            ),
            metadata=metadata,
            image=ImageInfo(
                media_type=validated.media_type,
                width=validated.width,
                height=validated.height,
                size_bytes=validated.size_bytes,
            ),
            items=items,
            totals=sum_profiles(item.nutrition for item in items),
        )
        logger.info(
            "meal analysed",
            extra={
                "analysis_id": str(response.analysis_id),
                "item_count": len(items),
                "is_mock": is_mock,
                "image_media_type": validated.media_type,
                "image_size_bytes": validated.size_bytes,
            },
        )
        return response
