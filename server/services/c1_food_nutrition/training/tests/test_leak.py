from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
from c1_training.fingerprint import Bits, fingerprint_from_gray
from c1_training.leak import audit, copies_to_drop, mark_dropped, path_key, reference_distances
from c1_training.manifest import Item
from numpy.typing import NDArray

PatternFactory = Callable[..., NDArray[np.uint8]]
RowFactory = Callable[..., dict[str, str]]
Fps = list[tuple[Bits, Bits]]


def item(name: str, split: str, group: str, labels: tuple[str, ...] = ("rice",)) -> Item:
    return Item(Path("/data") / f"{name}.jpg", split, labels, group, "kaggle_sl26")


@pytest.fixture
def fp(pattern: PatternFactory) -> Callable[..., tuple[Bits, Bits]]:
    def make(seed: int, flip: bool = False) -> tuple[Bits, Bits]:
        g = pattern(seed, 16, 17)[:, :, 0]
        return fingerprint_from_gray(np.ascontiguousarray(g[:, ::-1]) if flip else g)

    return make


ITEMS = [
    item("t1", "train", "g1"),
    item("t2", "train", "g2"),
    item("t3", "train", "g3", ("dhal",)),
    item("v1", "valid", "g4"),
    item("s1", "test", "g5"),
    item("s2", "test", "g6"),
]


@pytest.fixture
def fps(fp: Callable[..., tuple[Bits, Bits]]) -> Fps:
    # t1 is a mirrored copy of test s1; t3 copies test s2 but has other labels; v1 is new.
    return [fp(1, flip=True), fp(2), fp(3), fp(4), fp(1), fp(3)]


def test_audit_finds_closest_training_image(fps: Fps) -> None:
    by_name = {r.image.name: r for r in audit(ITEMS, fps)}
    assert set(by_name) == {"v1.jpg", "s1.jpg", "s2.jpg"}
    assert by_name["s1.jpg"].dist == 0
    assert by_name["s1.jpg"].closest_train.name == "t1.jpg"
    assert not by_name["s1.jpg"].same_group
    assert by_name["v1.jpg"].dist > 30


def test_reference_distances_skip_same_scene(fp: Callable[..., tuple[Bits, Bits]]) -> None:
    items = [item("a", "train", "g1"), item("b", "train", "g1"), item("c", "train", "g2")]
    ref = reference_distances(items, [fp(1), fp(1), fp(2)])
    assert len(ref) == 3 and min(ref) > 30  # a and b are identical but in the same scene


def test_copies_to_drop_with_and_without_same_labels(fps: Fps) -> None:
    t1, t3 = path_key(Path("/data/t1.jpg")), path_key(Path("/data/t3.jpg"))
    assert copies_to_drop(ITEMS, fps, max_dist=30) == {t1: "test", t3: "test"}
    assert copies_to_drop(ITEMS, fps, max_dist=30, same_labels=True) == {t1: "test"}


def test_mark_dropped_changes_only_keep_rows(row: RowFactory, tmp_path: Path) -> None:
    rows = [row("a", processed="_processed/x/a.jpg"), row("b"), row("c", role="mirror_copy")]
    drop = {
        path_key(tmp_path / "_processed/x/a.jpg"): "test",
        path_key(tmp_path / "raw/food_detect/c.png"): "valid",
    }
    assert mark_dropped(rows, tmp_path, drop, "copy of a {split} image") == 1
    assert rows[0]["role"] == "leak_dropped"
    assert rows[0]["clean_note"] == "copy of a test image"
    assert rows[1]["role"] == "keep" and rows[2]["role"] == "mirror_copy"
