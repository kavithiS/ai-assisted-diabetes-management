"""Image decoding and model input preparation (OpenCV + NumPy, no PyTorch)."""

import cv2
import numpy as np
from numpy.typing import NDArray

from c4_foot_monitoring.ml.interfaces import BgrImage

#: Input size and ImageNet statistics used by the ResNet50 training notebook.
INPUT_SIZE = 224
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def decode_image(data: bytes) -> BgrImage | None:
    """Decode JPEG/PNG bytes to a BGR image, or None when the bytes are not an image."""
    buffer = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        return None
    return np.asarray(image, dtype=np.uint8)


def to_model_input(image: BgrImage) -> NDArray[np.float32]:
    """BGR image → normalised RGB array of shape (1, 3, 224, 224).

    Matches torchvision's ``Resize((224, 224))``, ``ToTensor()`` and ``Normalize(...)``.
    The training notebook resized with PIL; OpenCV's bilinear resize gives slightly different
    pixels, which is a known, small difference.
    """
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_LINEAR)
    scaled = resized.astype(np.float32) / 255.0
    normalised = (scaled - IMAGENET_MEAN) / IMAGENET_STD
    return np.ascontiguousarray(normalised.transpose(2, 0, 1)[np.newaxis], dtype=np.float32)
