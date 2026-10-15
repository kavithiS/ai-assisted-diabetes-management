from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
from c1_training.preprocess import (
    EXTRA_COLUMNS,
    Processed,
    merge_rows,
    out_rel,
    process_image,
    target_size,
)
from numpy.typing import NDArray

RowFactory = Callable[..., dict[str, str]]
PatternFactory = Callable[..., NDArray[np.uint8]]


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        ((1000, 500), (512, 256, "")),
        ((500, 1000), (256, 512, "")),
        ((256, 400), (256, 400, "")),
        ((200, 300), (200, 300, "small")),
        ((641, 480), (342, 256, "")),
    ],
)
def test_target_size(size: tuple[int, int], expected: tuple[int, int, str]) -> None:
    assert target_size(*size, short=256) == expected


def test_out_rel_is_stable_and_uses_forward_slashes() -> None:
    rel = out_rel("food_detect:a.jpg", "food_detect")
    assert rel.startswith("_processed/food_detect/") and rel.endswith(".jpg")
    assert rel == out_rel("food_detect:a.jpg", "food_detect")
    assert rel != out_rel("food_detect:b.jpg", "food_detect")


def test_merge_prefers_new_then_previous(row: RowFactory) -> None:
    rows = [row("a"), row("b"), row("c")]
    done = {"a": Processed("a", "_processed/x/a.jpg", 10, 20, "RGB", 10, 20, "small", "")}
    previous = {"b": {k: f"old-{k}" for k in EXTRA_COLUMNS} | {"role": "keep"}}
    out = merge_rows(rows, done, previous)
    assert out[0]["processed_rel_path"] == "_processed/x/a.jpg" and out[0]["proc_w"] == "10"
    assert out[1]["processed_rel_path"] == "old-processed_rel_path"
    assert all(out[2][k] == "" for k in EXTRA_COLUMNS)


def test_merge_keeps_leak_fix_drops(row: RowFactory) -> None:
    rows = [row("a"), row("b")]
    note = "near-copy of a test image (fingerprint distance <= 30, 2026-10-15)"
    previous = {
        "a": {"role": "leak_dropped", "clean_note": note},
        "b": {"role": "leak_dropped", "clean_note": "same scene as a test image"},
    }
    out = merge_rows(rows, {}, previous)
    assert out[0]["role"] == "leak_dropped" and out[0]["clean_note"] == note
    assert out[1]["role"] == "keep"  # only the leak_fix drops are carried over


def test_process_image_resizes_and_flattens(pattern: PatternFactory, tmp_path: Path) -> None:
    image_module = pytest.importorskip("PIL.Image")
    rgba = np.dstack([pattern(1, 300, 600), np.full((300, 600), 128, dtype=np.uint8)])
    image_module.fromarray(rgba, "RGBA").save(tmp_path / "big.png")
    image_module.fromarray(pattern(2, 100, 120)).save(tmp_path / "small.png")

    big = process_image(tmp_path / "big.png", tmp_path / "out" / "big.jpg", 256)
    small = process_image(tmp_path / "small.png", tmp_path / "out" / "small.jpg", 256)

    assert big == (600, 300, "RGBA", 512, 256, "")
    assert small == (120, 100, "RGB", 120, 100, "small")
    with image_module.open(tmp_path / "out" / "big.jpg") as im:
        assert im.mode == "RGB" and im.size == (512, 256)
