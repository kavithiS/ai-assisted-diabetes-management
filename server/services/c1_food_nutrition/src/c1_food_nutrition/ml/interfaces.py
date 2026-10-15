"""Model-facing interfaces. Services depend on these protocols, never on concrete models.

A real EfficientNetV2 / MobileNetV3 recogniser (Phase 1+) only needs to satisfy
``FoodRecognizer`` to replace the mock without any API or schema change.
"""

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

#: Decoded image in OpenCV's BGR channel order, shape (height, width, 3), dtype uint8.
BgrImage = NDArray[np.uint8]


@dataclass(frozen=True, slots=True)
class Region:
    """Normalised [0, 1] image region (x, y = top-left corner)."""

    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class RecognizedFood:
    """One food detected in an image."""

    label: str
    confidence: float
    food_code: str | None = None
    region: Region | None = None
    #: Set when ``food_code`` is only a close or partial match for ``label``.
    match_note: str | None = None


@dataclass(frozen=True, slots=True)
class PortionEstimate:
    """Estimated portion for one recognised food."""

    grams: float
    method: str
    household_measure: str | None = None
    confidence: float | None = None


class FoodRecognizer(Protocol):
    """Recognises (possibly multiple) foods in a meal image."""

    @property
    def model_name(self) -> str:
        """Human-readable model identifier."""
        ...

    @property
    def model_version(self) -> str:
        """Version of the weights / model artefact."""
        ...

    @property
    def is_mock(self) -> bool:
        """True if this recogniser returns synthetic output."""
        ...

    def recognize(self, image: BgrImage) -> list[RecognizedFood]:
        """Return every food found in ``image``."""
        ...


class PortionEstimator(Protocol):
    """Estimates the portion size of a recognised food."""

    @property
    def is_mock(self) -> bool:
        """True if this estimator returns synthetic output."""
        ...

    def estimate(
        self, image: BgrImage, food: RecognizedFood, reference_object: str | None
    ) -> PortionEstimate:
        """Estimate the portion of ``food`` in ``image``.

        ``reference_object`` is reserved for TAF portion calibration and currently unused.
        """
        ...
