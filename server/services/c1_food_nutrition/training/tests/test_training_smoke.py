"""Smoke tests for the PyTorch code. Skipped unless torch, torchvision and Pillow are installed.

They train for one epoch on a few generated images with random weights (no download), on the
processor. They check that the code runs and writes its outputs, not that it learns.
"""

import json
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

RowFactory = Callable[..., dict[str, str]]
ManifestWriter = Callable[[Path, Sequence[dict[str, str]]], Path]
PatternFactory = Callable[..., NDArray[np.uint8]]


def test_stage2_default_input_size_is_256() -> None:
    from c1_training import stage2

    assert stage2.parse_args([]).size == 256


def test_build_model_and_load_backbone(tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")
    pytest.importorskip("torchvision")
    from c1_training.model import build_model, load_backbone

    source = build_model("mobilenet_v3_large", 5, pretrained=False)
    torch.save({"arch": "mobilenet_v3_large", "state": source.state_dict()}, tmp_path / "s1.pt")
    target = build_model("mobilenet_v3_large", 3, pretrained=False)
    loaded = load_backbone(target, tmp_path / "s1.pt")
    assert loaded == len(target.state_dict()) - 2  # final weight and bias differ in shape
    with torch.no_grad():
        assert target.eval()(torch.zeros(1, 3, 64, 64)).shape == (1, 3)
    with pytest.raises(ValueError, match="unknown arch"):
        build_model("resnet", 3, pretrained=False)


def test_stage2_one_epoch(
    row: RowFactory,
    write_manifest: ManifestWriter,
    pattern: PatternFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("torch")
    pytest.importorskip("torchvision")
    image_module = pytest.importorskip("PIL.Image")
    from c1_training import stage2

    rows: list[dict[str, str]] = []
    layout = [("train", 6), ("valid", 2), ("test", 2)]
    for split, n in layout:
        for k in range(n):
            name = f"{split}{k}"
            rel = f"_processed/food_detect/{name}.jpg"
            (tmp_path / "_processed" / "food_detect").mkdir(parents=True, exist_ok=True)
            image_module.fromarray(pattern(k + 10 * len(rows), 40, 40)).save(tmp_path / rel)
            labels = "rice|dhal" if k % 2 else "rice"
            rows.append(row(name, split=split, classes=labels, processed=rel))
    (tmp_path / "_curation").mkdir()
    write_manifest(tmp_path / "_curation" / "processed_manifest.csv", rows)
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")

    args = stage2.parse_args(
        [
            "--data-dir",
            str(tmp_path),
            "--out-dir",
            str(tmp_path / "runs"),
            "--tag",
            "smoke",
            "--no-pretrained",
            "--epochs",
            "1",
            "--bs",
            "4",
            "--size",
            "32",
            "--workers",
            "0",
        ]
    )
    report = stage2.run(args)

    assert report["run"] == "stage2_mobilenet_v3_large_imagenet_seed0_smoke"
    assert report["n_classes"] == 2
    assert report["n_images"] == {"train": 6, "valid": 2, "test": 2}
    assert (report["size"], report["batch_size"], report["tag"]) == (32, 4, "smoke")
    assert 0.0 <= report["test_mAP"] <= 1.0
    saved = json.loads((tmp_path / "runs" / f"{report['run']}_report.json").read_text())
    assert saved["n_classes"] == 2
    assert (tmp_path / "runs" / f"{report['run']}.pt").exists()
