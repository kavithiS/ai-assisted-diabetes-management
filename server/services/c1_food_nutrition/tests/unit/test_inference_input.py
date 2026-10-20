import numpy as np
import pytest

from c1_food_nutrition.ml.inference_input import (
    IMAGENET_MEAN,
    IMAGENET_STD,
    STORED_SHORT_SIDE,
    prepare_input,
)


def solid_bgr(blue: int, green: int, red: int, height: int = 40, width: int = 60) -> np.ndarray:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:, :] = (blue, green, red)
    return image


def test_output_shape_dtype_and_channel_order() -> None:
    out = prepare_input(solid_bgr(10, 100, 200), 32)
    assert out.shape == (3, 32, 32) and out.dtype == np.float32
    # BGR (10, 100, 200) becomes RGB (200, 100, 10): channel 0 is red.
    expected = (np.array([200, 100, 10], dtype=np.float32) / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
    np.testing.assert_allclose(out[:, 5, 5], expected, rtol=1e-5)


def test_large_images_are_shrunk_first_small_ones_are_not_enlarged() -> None:
    big = np.random.default_rng(0).integers(0, 256, size=(1200, 1600, 3), dtype=np.uint8)
    assert prepare_input(big, 64).shape == (3, 64, 64)
    assert STORED_SHORT_SIDE == 256
    tiny = solid_bgr(1, 2, 3, height=8, width=8)
    assert prepare_input(tiny, 64).shape == (3, 64, 64)  # only the final resize enlarges


@pytest.mark.parametrize("shape", [(0, 10, 3), (10, 10), (10, 10, 4)])
def test_bad_shapes_are_rejected(shape: tuple[int, ...]) -> None:
    with pytest.raises(ValueError, match="expected"):
        prepare_input(np.zeros(shape, dtype=np.uint8), 32)
