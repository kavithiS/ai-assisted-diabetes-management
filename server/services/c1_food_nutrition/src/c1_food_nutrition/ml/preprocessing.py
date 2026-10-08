"""Image decoding and preprocessing (OpenCV only; Albumentations transforms arrive in Phase 1)."""

import cv2
import numpy as np

from c1_food_nutrition.ml.interfaces import BgrImage


def decode_image(data: bytes) -> BgrImage | None:
    """Decode encoded image bytes into a BGR array with ``cv2.imdecode``.

    Returns:
        The decoded image, or ``None`` if OpenCV cannot decode the bytes.
    """
    if not data:
        return None
    buffer = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        return None
    return np.asarray(image, dtype=np.uint8)
