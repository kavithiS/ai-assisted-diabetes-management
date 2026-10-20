"""Model-facing interfaces. Services depend on these, never on a concrete model.

The trained ResNet50 classifier only needs to satisfy ``FootClassifier`` to replace the mock
without any API or schema change.
"""

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from c4_foot_monitoring.config import FootLabel

#: Decoded image in OpenCV's BGR channel order, shape (height, width, 3), dtype uint8.
BgrImage = NDArray[np.uint8]


@dataclass(frozen=True, slots=True)
class FootClassification:
    """The model's answer for one foot photo."""

    label: FootLabel
    #: Model score of ``label`` (0 to 1). INTERNAL ONLY: never sent to the patient.
    confidence: float


class FootClassifier(Protocol):
    """Classifies a foot photo as normal or ulcer."""

    @property
    def model_name(self) -> str:
        """Human-readable model identifier."""
        ...

    @property
    def model_version(self) -> str:
        """Version of the weights."""
        ...

    @property
    def is_mock(self) -> bool:
        """True if this classifier returns synthetic output."""
        ...

    def classify(self, image: BgrImage) -> FootClassification:
        """Classify one decoded image."""
        ...
