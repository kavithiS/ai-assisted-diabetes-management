"""MOCK model implementations for Phase 0.

Everything returned here is a SYNTHETIC PLACEHOLDER used to exercise the API contract.
It is not real food recognition or portion estimation, and results are always flagged
with ``meta.is_mock = true``.
"""

from c1_food_nutrition.ml.interfaces import BgrImage, PortionEstimate, RecognizedFood, Region

MOCK_MODEL_NAME = "mock-recognizer"
MOCK_MODEL_VERSION = "0.0.0-mock"


class MockFoodRecognizer:
    """Returns two fixed, obviously synthetic items to mimic a mixed-dish result."""

    @property
    def model_name(self) -> str:
        """Identifier reported in ``meta.model_name``."""
        return MOCK_MODEL_NAME

    @property
    def model_version(self) -> str:
        """Identifier reported in ``meta.model_version``."""
        return MOCK_MODEL_VERSION

    @property
    def is_mock(self) -> bool:
        """Always true."""
        return True

    def recognize(self, image: BgrImage) -> list[RecognizedFood]:
        """Ignore the image and return fixed placeholder items."""
        return [
            RecognizedFood(
                label="mock_item_a",
                confidence=0.5,
                food_code="MOCK-0001",
                region=Region(x=0.0, y=0.0, width=0.5, height=1.0),
            ),
            RecognizedFood(
                label="mock_item_b",
                confidence=0.5,
                food_code="MOCK-0002",
                region=Region(x=0.5, y=0.0, width=0.5, height=1.0),
            ),
        ]


class MockPortionEstimator:
    """Returns a fixed placeholder portion for every item."""

    #: Synthetic placeholder; not an estimate of any real portion.
    PLACEHOLDER_GRAMS = 100.0

    @property
    def is_mock(self) -> bool:
        """Always true."""
        return True

    def estimate(
        self, image: BgrImage, food: RecognizedFood, reference_object: str | None
    ) -> PortionEstimate:
        """Return the placeholder portion; ``reference_object`` is intentionally unused."""
        return PortionEstimate(grams=self.PLACEHOLDER_GRAMS, method="mock", confidence=0.5)
