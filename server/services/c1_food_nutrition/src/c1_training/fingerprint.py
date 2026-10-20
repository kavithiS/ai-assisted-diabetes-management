"""256-bit picture fingerprints for finding near-copies.

A 17 x 16 grey thumbnail; each bit says whether a pixel is brighter than its right neighbour.
The mirrored picture gets its own fingerprint, so a flipped copy is also found. Distance is the
number of differing bits: 0 means the same picture, up to about 30 is almost always the same
shot, 60 and above are different pictures.
"""

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

THUMB_WIDTH = 17
THUMB_HEIGHT = 16
BITS = (THUMB_WIDTH - 1) * THUMB_HEIGHT

Bits = NDArray[np.bool_]


def fingerprint_from_gray(gray: NDArray[np.uint8]) -> tuple[Bits, Bits]:
    """Return ``(fingerprint, mirrored fingerprint)`` of a 16 x 17 grey thumbnail."""
    if gray.shape != (THUMB_HEIGHT, THUMB_WIDTH):
        raise ValueError(f"expected a {THUMB_HEIGHT}x{THUMB_WIDTH} thumbnail, got {gray.shape}")
    a = gray.astype(np.int16)
    m = a[:, ::-1]
    return (a[:, 1:] > a[:, :-1]).flatten(), (m[:, 1:] > m[:, :-1]).flatten()


def load_gray_thumbnail(path: Path) -> NDArray[np.uint8]:
    """Open an image with Pillow and return its 16 x 17 grey thumbnail (training env only)."""
    from PIL import Image  # type: ignore[import-not-found, unused-ignore]

    with Image.open(path) as im:
        gray = im.convert("L").resize((THUMB_WIDTH, THUMB_HEIGHT), Image.BILINEAR)
    return np.asarray(gray, dtype=np.uint8)


def fingerprint(path: Path) -> tuple[Bits, Bits]:
    """Fingerprint of the image file at ``path``."""
    return fingerprint_from_gray(load_gray_thumbnail(path))


def distances(query: tuple[Bits, Bits], stack: NDArray[np.bool_]) -> NDArray[np.int64]:
    """Distance from ``query`` (or its mirror, whichever is closer) to each row of ``stack``."""
    plain = (stack != query[0]).sum(axis=1)
    mirrored = (stack != query[1]).sum(axis=1)
    result: NDArray[np.int64] = np.minimum(plain, mirrored).astype(np.int64)
    return result
