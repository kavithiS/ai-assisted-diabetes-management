from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from c4_foot_monitoring.config import Settings
from c4_foot_monitoring.ml.interfaces import FootClassification
from c4_foot_monitoring.ml.preprocessing import INPUT_SIZE, decode_image, to_model_input
from c4_foot_monitoring.ml.risk import risk_band_for
from c4_foot_monitoring.services.image_validation import detect_image_type, normalize_media_type


@pytest.mark.parametrize(
    ("label", "confidence", "band"),
    [
        ("ulcer", 0.99, "High"),
        ("ulcer", 0.51, "High"),
        ("normal", 0.95, "Low"),
        ("normal", 0.8, "Low"),
        ("normal", 0.79, "Medium"),
    ],
)
def test_risk_band_rule(label: str, confidence: float, band: str) -> None:
    result = FootClassification(label=label, confidence=confidence)  # type: ignore[arg-type]

    assert risk_band_for(result, 0.8) == band


def test_model_path_requires_class_order() -> None:
    with pytest.raises(ValidationError, match="FOOT_MODEL_CLASSES"):
        Settings(foot_model_path=Path("model.pth"))


def test_class_order_must_name_both_classes() -> None:
    with pytest.raises(ValidationError):
        Settings(foot_model_path=Path("model.pth"), foot_model_classes=("ulcer", "ulcer"))


def test_only_decodable_image_types_are_allowed() -> None:
    with pytest.raises(ValidationError):
        Settings(allowed_image_types=frozenset({"image/gif"}))


def test_detect_and_normalize_media_types() -> None:
    assert detect_image_type(b"\xff\xd8\xff\xe0rest") == "image/jpeg"
    assert detect_image_type(b"\x89PNG\r\n\x1a\nrest") == "image/png"
    assert detect_image_type(b"GIF89a") is None
    assert normalize_media_type("IMAGE/JPG; charset=x") == "image/jpeg"
    assert normalize_media_type(None) is None


def test_model_input_shape_and_normalisation(jpeg_bytes: bytes) -> None:
    image = decode_image(jpeg_bytes)
    assert image is not None

    batch = to_model_input(image)

    assert batch.shape == (1, 3, INPUT_SIZE, INPUT_SIZE)
    assert batch.dtype == np.float32
    # A white pixel maps to (1 - mean) / std for each channel.
    white = to_model_input(np.full((10, 10, 3), 255, dtype=np.uint8))
    assert white[0, 0, 0, 0] == pytest.approx((1 - 0.485) / 0.229)


def test_decode_rejects_garbage() -> None:
    assert decode_image(b"not an image") is None
