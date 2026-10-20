from collections.abc import Callable, Sequence
from pathlib import Path

from c1_training.manifest import (
    items_from_rows,
    load_manifest,
    read_rows,
    split_counts,
    split_items,
    summary,
)

RowFactory = Callable[..., dict[str, str]]
ManifestWriter = Callable[[Path, Sequence[dict[str, str]]], Path]


def test_keeps_only_keep_rows_with_classes(row: RowFactory, tmp_path: Path) -> None:
    rows = [
        row("a"),
        row("b", role="leak_dropped"),
        row("c", classes=""),
        row("d", dataset="foodbd"),
    ]
    items, classes = items_from_rows(rows, tmp_path, ["food_detect"])
    assert [i.path.name for i in items] == ["a.png"]
    assert classes == ["rice"]


def test_min_scenes_counts_distinct_train_groups(row: RowFactory, tmp_path: Path) -> None:
    rows = [
        row("r1", classes="rice", group="g1"),
        row("r2", classes="rice", group="g1"),  # same scene, counts once
        row("r3", classes="rice", group="g2"),
        row("d1", classes="dhal", group="g3"),
        row("d2", classes="dhal", group="g4", split="test"),  # test scenes do not count
    ]
    _, classes = items_from_rows(rows, tmp_path, ["food_detect"], min_train_scenes=2)
    assert classes == ["rice"]


def test_dropped_classes_are_removed_from_labels(row: RowFactory, tmp_path: Path) -> None:
    rows = [
        row("a", classes="rice|dhal", group="g1"),
        row("b", classes="rice", group="g2"),
        row("c", classes="dhal", split="test"),
    ]
    items, classes = items_from_rows(rows, tmp_path, ["food_detect"], min_train_scenes=2)
    assert classes == ["rice"]
    assert [i.labels for i in items] == [("rice",), ("rice",)]  # "c" has no label left


def test_processed_copy_is_preferred(row: RowFactory, tmp_path: Path) -> None:
    rows = [row("a", processed="_processed/food_detect/x.jpg"), row("b")]
    items, _ = items_from_rows(rows, tmp_path, ["food_detect"])
    assert items[0].path == tmp_path / "_processed/food_detect/x.jpg"
    assert items[1].path == tmp_path / "raw/food_detect/b.png"


def test_train_only_dataset_adds_train_rows_only(row: RowFactory, tmp_path: Path) -> None:
    rows = [
        row("sl_tr"),
        row("sl_te", split="test"),
        row("bd_tr", dataset="pust", classes="rice|egg"),
        row("bd_va", dataset="pust", split="valid"),
        row("bd_te", dataset="pust", split="test"),
    ]
    items, classes = items_from_rows(rows, tmp_path, ["food_detect", "pust"], train_only=["pust"])
    assert sorted(i.path.stem for i in items) == ["bd_tr", "sl_te", "sl_tr"]
    assert classes == ["egg", "rice"]
    # without train_only the extra dataset's valid/test rows are used too
    all_items, _ = items_from_rows(rows, tmp_path, ["food_detect", "pust"])
    assert len(all_items) == 5


def test_split_items_limits_labels_and_skips_unlabelled(row: RowFactory, tmp_path: Path) -> None:
    rows = [
        row("a", dataset="pust", split="test", classes="egg|samosa"),
        row("b", dataset="pust", split="test", classes="samosa"),
        row("c", dataset="pust", split="train", classes="egg"),
        row("d", dataset="pust", split="test", classes="egg", role="leak_dropped"),
        row("e", split="test", classes="egg"),
    ]
    items = split_items(rows, tmp_path, ["pust"], ["egg", "rice"], "test")
    assert [(i.path.stem, i.labels) for i in items] == [("a", ("egg",))]


def test_load_manifest_and_counts(
    row: RowFactory, write_manifest: ManifestWriter, tmp_path: Path
) -> None:
    manifest = write_manifest(
        tmp_path / "m.csv",
        [row("a"), row("b", split="valid"), row("c", split="test"), row("d", split="test")],
    )
    fields, rows = read_rows(manifest)
    assert fields[0] == "image_id" and len(rows) == 4
    items, classes = load_manifest(manifest, tmp_path, ["food_detect"])
    assert split_counts(items) == {"train": 1, "valid": 1, "test": 2}
    expected = "4 images, 1 classes, splits {'train': 1, 'valid': 1, 'test': 2}"
    assert summary(items, classes) == expected
