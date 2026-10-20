from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
from c1_training.cleaning import check_file, clean_rows
from numpy.typing import NDArray

RowFactory = Callable[..., dict[str, str]]
PatternFactory = Callable[..., NDArray[np.uint8]]


def test_broken_files_get_their_status(row: RowFactory) -> None:
    rows = [row("a"), row("b"), row("c"), row("d", role="mirror_copy")]
    status = {
        rows[0]["rel_path"]: "ok",
        rows[1]["rel_path"]: "missing_file",
        rows[2]["rel_path"]: "unreadable",
        rows[3]["rel_path"]: "unreadable",  # not 'keep', so left alone
    }
    changed, leaking = clean_rows(rows, status)
    assert [r["role"] for r in rows] == ["keep", "missing_file", "unreadable", "mirror_copy"]
    assert [r["role_original"] for r in rows] == ["keep", "keep", "keep", "mirror_copy"]
    assert changed == {"missing_file": 1, "unreadable": 1}
    assert leaking == 0


def test_leaking_group_keeps_most_protected_split(row: RowFactory) -> None:
    rows = [
        row("a", group="g1", split="train"),
        row("b", group="g1", split="valid"),
        row("c", group="g1", split="test"),
        row("d", group="g2", split="train"),
        row("e", group="g2", split="valid"),
        row("f", group="g3", split="train"),
    ]
    changed, leaking = clean_rows(rows, {})
    assert leaking == 2
    assert [r["role"] for r in rows] == [
        "leak_dropped",
        "leak_dropped",
        "keep",
        "leak_dropped",
        "keep",
        "keep",
    ]
    assert rows[0]["clean_note"] == "same scene as a test image"
    assert rows[3]["clean_note"] == "same scene as a valid image"
    assert changed == {"leak_dropped": 3}


def test_groups_are_per_dataset(row: RowFactory) -> None:
    rows = [
        row("a", group="g1", split="train", dataset="food_detect"),
        row("b", group="g1", split="test", dataset="shorteats"),
    ]
    _, leaking = clean_rows(rows, {})
    assert leaking == 0


def test_check_file_on_generated_images(pattern: PatternFactory, tmp_path: Path) -> None:
    image_module = pytest.importorskip("PIL.Image")
    good = tmp_path / "good.jpg"
    image_module.fromarray(pattern(1, 64, 64)).save(good, "JPEG")
    truncated = tmp_path / "truncated.jpg"
    truncated.write_bytes(good.read_bytes()[:200])
    not_image = tmp_path / "text.jpg"
    not_image.write_text("not an image", encoding="utf-8")
    assert check_file(good) == "ok"
    assert check_file(truncated) == "unreadable"
    assert check_file(not_image) == "unreadable"
    assert check_file(tmp_path / "missing.jpg") == "missing_file"
