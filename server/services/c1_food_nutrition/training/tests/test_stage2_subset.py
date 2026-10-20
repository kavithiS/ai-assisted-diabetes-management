"""Scoring a run with extra classes on exactly the baseline photos and classes (numpy only)."""

from pathlib import Path

import numpy as np
import pytest
from c1_training.manifest import Item
from c1_training.metrics import mean_average_precision
from c1_training.stage2 import base_subset, parse_args, subset_metrics


def _item(name: str, split: str, labels: tuple[str, ...]) -> Item:
    return Item(Path(f"/x/{name}.jpg"), split, labels, name, "food_detect")


def test_subset_metrics_uses_only_selected_rows_and_columns() -> None:
    labels = np.array([[1, 0, 1], [0, 1, 0], [1, 1, 1]], dtype=float)
    scores = np.array([[0.9, 0.1, 0.2], [0.2, 0.8, 0.9], [0.7, 0.6, 0.1]])
    m, f1 = subset_metrics(scores, labels, [0, 1], [0, 1])
    assert m == mean_average_precision(labels[:2, :2], scores[:2, :2])
    assert f1 == 1.0  # rows 0-1, columns 0-1 are all predicted correctly at 0.5


def test_base_subset_finds_baseline_rows_and_columns() -> None:
    split = {
        "train": [_item("t", "train", ("rice",))],
        "valid": [_item("v1", "valid", ("rice",)), _item("v2", "valid", ("samosa",))],
        "test": [_item("s2", "test", ("samosa",)), _item("s1", "test", ("dhal", "samosa"))],
    }
    index = {"dhal": 0, "rice": 1, "samosa": 2}
    base_items = [_item("v1", "valid", ("rice",)), _item("s1", "test", ("dhal",))]
    rows, cols = base_subset(split, index, base_items, ["dhal", "rice"])
    assert rows == {"valid": [0], "test": [1]}
    assert cols == [0, 1]


def test_base_subset_rejects_missing_classes_or_images() -> None:
    split = {"valid": [_item("v1", "valid", ("rice",))], "test": []}
    with pytest.raises(ValueError, match="base classes missing"):
        base_subset(split, {"rice": 0}, [], ["rice", "dhal"])
    with pytest.raises(ValueError, match="base images missing"):
        base_subset(split, {"rice": 0}, [_item("gone", "test", ("rice",))], ["rice"])


def test_extras_train_only_flag_defaults_off() -> None:
    assert parse_args([]).extras_train_only is False
    assert parse_args(["--also", "pust", "--extras-train-only"]).extras_train_only is True
