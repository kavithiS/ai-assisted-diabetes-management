"""Read the image manifest into training items. Uses the standard library only."""

import collections
import csv
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

#: The public Sri Lankan image sets used for Stage 2.
SL_SETS: tuple[str, ...] = ("food_detect", "shorteats", "sl_meal", "kaggle_sl26")
SPLITS: tuple[str, ...] = ("train", "valid", "test")

Row = dict[str, str]


@dataclass(frozen=True, slots=True)
class Item:
    """One training image with its clean labels."""

    path: Path
    split: str
    labels: tuple[str, ...]
    group: str
    dataset: str


def read_rows(path: Path) -> tuple[list[str], list[Row]]:
    """Return the header and every row of a manifest CSV."""
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def write_rows(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    """Write a manifest CSV with the given column order."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields))
        writer.writeheader()
        writer.writerows(rows)


def items_from_rows(
    rows: Iterable[Mapping[str, str]],
    root: Path,
    datasets: Iterable[str],
    min_train_scenes: int = 1,
) -> tuple[list[Item], list[str]]:
    """Build items from manifest rows.

    Only rows with ``role == keep`` and at least one class are used. Classes with fewer than
    ``min_train_scenes`` distinct train scene groups are dropped, and so are images left
    with no class. Splits come from ``suggested_split`` (split by scene group).
    """
    wanted = set(datasets)
    kept = [r for r in rows if r["dataset"] in wanted and r["role"] == "keep" and r["classes"]]
    scenes: dict[str, set[str]] = collections.defaultdict(set)
    for r in kept:
        if r["suggested_split"] == "train":
            for c in r["classes"].split("|"):
                scenes[c].add(r["group_id"])
    classes = sorted(c for c, s in scenes.items() if len(s) >= min_train_scenes)
    keep = set(classes)
    items: list[Item] = []
    for r in kept:
        labels = tuple(c for c in r["classes"].split("|") if c in keep)
        if labels:
            rel = r.get("processed_rel_path") or r["rel_path"]
            items.append(
                Item(
                    path=root / rel,
                    split=r["suggested_split"],
                    labels=labels,
                    group=r["group_id"],
                    dataset=r["dataset"],
                )
            )
    return items, classes


def load_manifest(
    manifest: Path, root: Path, datasets: Iterable[str], min_train_scenes: int = 1
) -> tuple[list[Item], list[str]]:
    """Read ``manifest`` and return ``(items, classes)``; see :func:`items_from_rows`."""
    _, rows = read_rows(manifest)
    return items_from_rows(rows, root, datasets, min_train_scenes)


def split_counts(items: Iterable[Item]) -> dict[str, int]:
    """Number of items per split."""
    return dict(collections.Counter(i.split for i in items))


def summary(items: Sequence[Item], classes: Sequence[str]) -> str:
    """One line describing the set."""
    return f"{len(items)} images, {len(classes)} classes, splits {split_counts(items)}"
