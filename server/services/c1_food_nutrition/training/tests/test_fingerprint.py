from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
from c1_training.fingerprint import BITS, distances, fingerprint, fingerprint_from_gray
from numpy.typing import NDArray

PatternFactory = Callable[..., NDArray[np.uint8]]


def test_shape_is_checked() -> None:
    with pytest.raises(ValueError, match="16x17"):
        fingerprint_from_gray(np.zeros((17, 16), dtype=np.uint8))


def test_identical_and_mirrored_pictures_have_distance_zero(pattern: PatternFactory) -> None:
    g = pattern(1, 16, 17)[:, :, 0]
    fp = fingerprint_from_gray(g)
    assert fp[0].shape == (BITS,)
    mirrored = np.ascontiguousarray(g[:, ::-1])
    stack = np.stack([fingerprint_from_gray(g)[0], fingerprint_from_gray(mirrored)[0]])
    assert distances(fp, stack).tolist() == [0, 0]


def test_different_pictures_are_far_apart(pattern: PatternFactory) -> None:
    fp = fingerprint_from_gray(pattern(1, 16, 17)[:, :, 0])
    others = np.stack([fingerprint_from_gray(pattern(s, 16, 17)[:, :, 0])[0] for s in range(2, 8)])
    assert distances(fp, others).min() > 30


def test_fingerprint_of_files(pattern: PatternFactory, tmp_path: Path) -> None:
    image_module = pytest.importorskip("PIL.Image")
    img = pattern(3, 120, 160)
    image_module.fromarray(img).save(tmp_path / "a.png")
    image_module.fromarray(np.ascontiguousarray(img[:, ::-1])).save(tmp_path / "flipped.png")
    image_module.fromarray(pattern(4, 120, 160)).save(tmp_path / "other.png")
    fp = fingerprint(tmp_path / "a.png")
    stack = np.stack([fingerprint(tmp_path / n)[0] for n in ("flipped.png", "other.png")])
    near, far = distances(fp, stack).tolist()
    assert near <= 10
    assert far > 30
