"""Tests for the trained recogniser, using a bundle with RANDOM weights.

Skipped unless PyTorch and torchvision are installed. They check the plumbing (loading,
checks, thresholds, labels, concept ids), not food-recognition quality.
"""

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from c1_food_nutrition.ml.labels import UnmappedClassError

BundleFactory = Callable[..., Path]


def image(seed: int = 0, height: int = 90, width: int = 120) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)


def test_recognizer_reports_every_class_at_threshold_zero(make_bundle: BundleFactory) -> None:
    from c1_food_nutrition.ml.torch_recognizer import TorchFoodRecognizer

    recognizer = TorchFoodRecognizer(make_bundle(threshold=0.0))
    assert recognizer.is_mock is False
    assert recognizer.model_name == "mobilenet_v3_large-multilabel"
    assert recognizer.model_version == "fixture-random-weights"
    assert recognizer.classes == ["kiribath", "lunu_miris", "hoppers"]
    assert recognizer.input_size == 64 and recognizer.threshold == 0.0

    foods = recognizer.recognize(image())
    assert sorted(f.label for f in foods) == ["hoppers", "kiribath", "lunu_miris"]
    assert [f.confidence for f in foods] == sorted((f.confidence for f in foods), reverse=True)
    assert all(0.0 <= f.confidence <= 1.0 for f in foods)
    codes = {f.label: f.food_code for f in foods}
    # food_code is the composition-table entry; None where there is no honest match.
    assert codes == {"kiribath": "SL_9", "lunu_miris": None, "hoppers": "SL_37"}
    assert all(f.region is None and f.match_note is None for f in foods)  # exact or no match


def test_threshold_override_and_empty_result(make_bundle: BundleFactory) -> None:
    from c1_food_nutrition.ml.torch_recognizer import TorchFoodRecognizer

    path = make_bundle(threshold=0.0)
    assert TorchFoodRecognizer(path, threshold=1.0).recognize(image()) == []
    scores = TorchFoodRecognizer(path).class_scores(image())
    assert scores.shape == (3,) and scores.dtype == np.float32


def test_bundle_can_use_a_validation_selected_threshold_for_one_class(
    make_bundle: BundleFactory,
) -> None:
    from c1_food_nutrition.ml.torch_recognizer import TorchFoodRecognizer

    path = make_bundle(
        threshold=1.0,
        class_thresholds={"kiribath": 0.0},
    )
    recognizer = TorchFoodRecognizer(path)
    assert recognizer.class_thresholds == {"kiribath": 0.0}
    assert [food.label for food in recognizer.recognize(image())] == ["kiribath"]

    # An explicit global override is useful for evaluation and intentionally
    # disables bundle-specific overrides.
    overridden = TorchFoodRecognizer(path, threshold=1.0)
    assert overridden.class_thresholds == {}
    assert overridden.recognize(image()) == []


def test_same_input_gives_same_scores(make_bundle: BundleFactory) -> None:
    from c1_food_nutrition.ml.torch_recognizer import TorchFoodRecognizer

    recognizer = TorchFoodRecognizer(make_bundle())
    np.testing.assert_array_equal(
        recognizer.class_scores(image(1)), recognizer.class_scores(image(1))
    )


def test_approximate_matches_carry_a_note(make_bundle: BundleFactory) -> None:
    from c1_food_nutrition.ml.torch_recognizer import TorchFoodRecognizer

    recognizer = TorchFoodRecognizer(make_bundle(classes=("chicken_bun", "kiribath")))
    notes = {f.label: f.match_note for f in recognizer.recognize(image())}
    assert notes["kiribath"] is None
    assert notes["chicken_bun"] == (
        "'chicken_bun': nutrition from table entry SL_11 "
        "(partial match: plain Bun; the filling is not included)"
    )


def test_unreviewed_class_stops_loading(make_bundle: BundleFactory) -> None:
    from c1_food_nutrition.ml.labels import UnreviewedClassError
    from c1_food_nutrition.ml.torch_recognizer import TorchFoodRecognizer

    with pytest.raises(UnreviewedClassError, match="almond"):
        TorchFoodRecognizer(make_bundle(classes=("kiribath", "almond")))


def test_unmapped_class_stops_loading(make_bundle: BundleFactory) -> None:
    from c1_food_nutrition.ml.torch_recognizer import TorchFoodRecognizer

    with pytest.raises(UnmappedClassError, match="no_such_food"):
        TorchFoodRecognizer(make_bundle(classes=("kiribath", "no_such_food")))


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"format": "other/v9"}, "unknown bundle format"),
        ({"classes": ["kiribath", "kiribath"]}, "empty or repeated"),
        ({"size": 8}, "bad size"),
        ({"threshold": 1.5}, "bad size"),
        ({"class_thresholds": {"unknown": 0.5}}, "unknown classes"),
        ({"class_thresholds": {"kiribath": 1.5}}, "between 0 and 1"),
        ({"class_thresholds": {"kiribath": "low"}}, "must be numbers"),
        ({"class_thresholds": []}, "label-to-number map"),
        ({"arch": "resnet50"}, "unsupported arch"),
        ({"classes": ("kiribath", "hoppers"), "n_outputs": 3}, "do not fit"),
    ],
)
def test_inconsistent_bundles_are_rejected(
    make_bundle: BundleFactory, overrides: dict[str, object], message: str
) -> None:
    from c1_food_nutrition.ml.bundle import ModelBundleError
    from c1_food_nutrition.ml.torch_recognizer import TorchFoodRecognizer

    with pytest.raises(ModelBundleError, match=message):
        TorchFoodRecognizer(make_bundle(**overrides))


def test_missing_file_and_missing_keys(make_bundle: BundleFactory, tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")
    from c1_food_nutrition.ml.bundle import ModelBundleError
    from c1_food_nutrition.ml.torch_recognizer import TorchFoodRecognizer

    with pytest.raises(ModelBundleError, match="not found"):
        TorchFoodRecognizer(tmp_path / "nope.pt")
    partial = tmp_path / "partial.pt"
    torch.save({"format": "c1-recognizer/v1"}, partial)
    with pytest.raises(ModelBundleError, match="lacks"):
        TorchFoodRecognizer(partial)
    junk = tmp_path / "junk.pt"
    junk.write_bytes(b"not a torch file")
    with pytest.raises(ModelBundleError, match="cannot read"):
        TorchFoodRecognizer(junk)
