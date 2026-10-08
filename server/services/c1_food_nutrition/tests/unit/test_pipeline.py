"""Service tests with fake (non-mock) components. All values are TEST FIXTURES."""

from datetime import UTC, datetime

import pytest

from c1_food_nutrition.ml.interfaces import BgrImage, PortionEstimate, RecognizedFood
from c1_food_nutrition.schemas.meal_analysis import MealAnalysisMetadata
from c1_food_nutrition.schemas.nutrition import (
    NutrientProfile,
    NutritionSourceCode,
    NutritionSourceRef,
)
from c1_food_nutrition.services.image_validation import ImageValidator
from c1_food_nutrition.services.pipeline import MealAnalysisService

pytestmark = pytest.mark.anyio

FIXTURE_PER_100G = NutrientProfile(energy_kcal=200.0, carbohydrate_g=30.0)
NOW = datetime(2026, 10, 3, tzinfo=UTC)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class BytesReader:
    def __init__(self, data: bytes) -> None:
        self._data = data

    async def read(self, size: int = -1) -> bytes:
        chunk, self._data = (
            (self._data, b"") if size < 0 else (self._data[:size], self._data[size:])
        )
        return chunk


class FakeRecognizer:
    model_name = "fake"
    model_version = "1"
    is_mock = False

    def recognize(self, image: BgrImage) -> list[RecognizedFood]:
        return [
            RecognizedFood(label="fixture_known", confidence=0.9, food_code="FIX-1"),
            RecognizedFood(label="fixture_unmatched", confidence=0.4, food_code=None),
        ]


class FakePortion:
    is_mock = False

    def __init__(self) -> None:
        self.reference_objects: list[str | None] = []

    def estimate(
        self, image: BgrImage, food: RecognizedFood, reference_object: str | None
    ) -> PortionEstimate:
        self.reference_objects.append(reference_object)
        return PortionEstimate(grams=50.0, method="model", confidence=0.8)


class FakeLookup:
    is_mock = False

    def per_100g(self, food_code: str) -> tuple[NutrientProfile, NutritionSourceRef] | None:
        if food_code == "FIX-1":
            return FIXTURE_PER_100G, NutritionSourceRef(
                source=NutritionSourceCode.USDA_FDC, source_food_id="fixture"
            )
        return None


async def test_non_mock_pipeline(jpeg_bytes: bytes) -> None:
    portion = FakePortion()
    service = MealAnalysisService(
        image_validator=ImageValidator(
            allowed_types={"image/jpeg"}, max_bytes=1_000_000, chunk_bytes=1024
        ),
        recognizer=FakeRecognizer(),
        portion_estimator=portion,
        nutrition_lookup=FakeLookup(),
        clock=lambda: NOW,
    )
    result = await service.analyze(
        image=BytesReader(jpeg_bytes),
        declared_content_type="image/jpeg",
        metadata=MealAnalysisMetadata(reference_object="card"),
    )

    assert result.meta.is_mock is False
    assert result.meta.warnings == []
    assert result.meta.generated_at == NOW
    known, unmatched = result.items
    assert known.nutrition.energy_kcal == pytest.approx(100.0)
    assert known.nutrition_source is not None
    assert unmatched.nutrition == NutrientProfile()
    assert unmatched.nutrition_source is None
    # Unknown nutrition for one item makes the total unknown rather than understated.
    assert result.totals.energy_kcal is None
    # reference_object is passed through to the portion estimator.
    assert portion.reference_objects == ["card", "card"]
