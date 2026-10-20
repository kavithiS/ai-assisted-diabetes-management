"""Export tests. The round trip is skipped unless torch, torchvision and Pillow are installed.

Images are SYNTHETIC fixtures and the weights are random: the tests check that training,
export and the service's recogniser agree on the file format, not that anything is learned.
"""

from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np
import pytest
from c1_training.export import THRESHOLDS, choose_threshold
from numpy.typing import NDArray

RowFactory = Callable[..., dict[str, str]]
ManifestWriter = Callable[[Path, Sequence[dict[str, str]]], Path]
PatternFactory = Callable[..., NDArray[np.uint8]]


def test_choose_threshold_picks_the_best_f1_and_ties_go_near_half() -> None:
    labels = np.array([[1], [1], [0], [0]])
    scores = np.array([[0.9], [0.7], [0.6], [0.2]])
    threshold, f1 = choose_threshold(labels, scores)
    assert f1 == 1.0
    assert threshold == 0.65  # 0.65 and 0.7 both separate the groups; 0.65 is nearer 0.5


def test_choose_threshold_with_no_good_split_still_returns_a_candidate() -> None:
    labels = np.array([[1], [0]])
    threshold, f1 = choose_threshold(labels, np.array([[0.1], [0.9]]))
    assert threshold in THRESHOLDS
    assert 0.0 <= f1 <= 1.0


def test_train_export_and_load_in_the_service_recogniser(
    row: RowFactory,
    write_manifest: ManifestWriter,
    pattern: PatternFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("torch")
    pytest.importorskip("torchvision")
    pytest.importorskip("cv2")  # the service recogniser needs OpenCV
    image_module = pytest.importorskip("PIL.Image")
    from c1_training import export, stage2

    from c1_food_nutrition.ml.torch_recognizer import TorchFoodRecognizer

    rows: list[dict[str, str]] = []
    (tmp_path / "_processed" / "food_detect").mkdir(parents=True)
    for split, n in (("train", 6), ("valid", 4), ("test", 2)):
        for k in range(n):
            name = f"{split}{k}"
            rel = f"_processed/food_detect/{name}.jpg"
            image_module.fromarray(pattern(len(rows) * 7 + k, 48, 48)).save(tmp_path / rel)
            labels = "kiribath|hoppers" if k % 2 else "kiribath"
            rows.append(row(name, split=split, classes=labels, processed=rel))
    (tmp_path / "_curation").mkdir()
    write_manifest(tmp_path / "_curation" / "processed_manifest.csv", rows)
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")
    runs = tmp_path / "runs"

    stage2.run(
        stage2.parse_args(
            [
                *["--data-dir", str(tmp_path), "--out-dir", str(runs), "--tag", "t"],
                *["--no-pretrained", "--epochs", "1", "--bs", "4", "--size", "64"],
                *["--workers", "0"],
            ]
        )
    )
    run_name = "stage2_mobilenet_v3_large_imagenet_seed0_t"
    summary = export.run(
        export.parse_args(["--data-dir", str(tmp_path), "--runs-dir", str(runs), "--run", run_name])
    )

    assert summary["classes"] == 2 and summary["size"] == 64
    assert summary["threshold"] in THRESHOLDS
    recognizer = TorchFoodRecognizer(runs / f"{run_name}_bundle.pt", threshold=0.0)
    assert recognizer.classes == ["hoppers", "kiribath"]
    assert recognizer.model_version == run_name
    bgr = pattern(3, 100, 130)[:, :, ::-1].copy()
    foods = recognizer.recognize(bgr)
    assert {f.label for f in foods} == {"hoppers", "kiribath"}
    assert {f.food_code for f in foods} == {"SL_37", "SL_9"}  # table entries, not concepts
    with pytest.raises(SystemExit, match="no input size"):
        # A report without an input size (an older run) needs --size.
        (runs / f"{run_name}_report.json").write_text(
            '{"min_scenes": 1, "extra_datasets": []}', encoding="utf-8"
        )
        export.run(
            export.parse_args(
                ["--data-dir", str(tmp_path), "--runs-dir", str(runs), "--run", run_name]
            )
        )
