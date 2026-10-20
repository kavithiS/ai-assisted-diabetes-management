"""MOCK foot classifier, used until the trained model exists.

Everything returned here is a SYNTHETIC PLACEHOLDER to exercise the API and the app. It is not
a real analysis, and every response is flagged with ``meta.is_mock = true``.
"""

import itertools
import threading

from c4_foot_monitoring.ml.interfaces import BgrImage, FootClassification

MOCK_MODEL_NAME = "mock"
MOCK_MODEL_VERSION = "0.0.0"

#: Cycled in order so a demo shows every risk band: Low, Medium, High (with the default cut-off).
_SEQUENCE = (
    FootClassification(label="normal", confidence=0.95),
    FootClassification(label="normal", confidence=0.6),
    FootClassification(label="ulcer", confidence=0.9),
)


class MockFootClassifier:
    """Ignores the image and returns the next placeholder result."""

    def __init__(self) -> None:
        self._results = itertools.cycle(_SEQUENCE)
        self._lock = threading.Lock()

    @property
    def model_name(self) -> str:
        return MOCK_MODEL_NAME

    @property
    def model_version(self) -> str:
        return MOCK_MODEL_VERSION

    @property
    def is_mock(self) -> bool:
        return True

    def classify(self, image: BgrImage) -> FootClassification:
        with self._lock:
            return next(self._results)
