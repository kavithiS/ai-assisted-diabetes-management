"""Turn a decoded upload into the array the model was trained on (numpy and OpenCV only).

Training saw images resized so the short side is 256 px (``c1_training.preprocess``), then
squashed to ``size`` x ``size`` and normalised with the ImageNet mean and standard deviation
(``c1_training.stage2``, evaluation transform). Do the same here, so a photo from a phone and
a stored training copy give the same input. OpenCV resizing is not byte-identical to Pillow's,
so small differences in the scores are expected.
"""

import cv2
import numpy as np
from numpy.typing import NDArray

from c1_food_nutrition.ml.interfaces import BgrImage

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
STORED_SHORT_SIDE = 256


def prepare_input(image: BgrImage, size: int) -> NDArray[np.float32]:
    """Return a float32 array of shape ``(3, size, size)``, RGB, normalised.

    Raises:
        ValueError: ``image`` is not a non-empty ``(height, width, 3)`` array.
    """
    if image.ndim != 3 or image.shape[2] != 3 or image.size == 0:
        raise ValueError(f"expected a (height, width, 3) image, got shape {image.shape}")
    height, width = image.shape[:2]
    short = min(height, width)
    shrunk: NDArray[np.uint8] = image
    if short > STORED_SHORT_SIDE:  # same shrink as the stored training copies (never enlarge)
        k = STORED_SHORT_SIDE / short
        new_w, new_h = max(1, round(width * k)), max(1, round(height * k))
        shrunk = np.asarray(
            cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA), dtype=np.uint8
        )
    squashed = cv2.resize(shrunk, (size, size), interpolation=cv2.INTER_LINEAR)
    rgb = cv2.cvtColor(squashed, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    normalised = (rgb - IMAGENET_MEAN) / IMAGENET_STD
    out: NDArray[np.float32] = np.ascontiguousarray(normalised.transpose(2, 0, 1))
    return out
