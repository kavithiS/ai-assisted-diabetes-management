"""Find training photos that are near-copies of validation or test photos, and drop them.

The valid/test photo is always kept; the train copy gets ``role = leak_dropped``. Image files
are never touched. All functions take precomputed fingerprints, so they need numpy only.
"""

import os
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from .fingerprint import Bits, distances
from .manifest import Item

Fingerprints = Sequence[tuple[Bits, Bits]]


@dataclass(frozen=True, slots=True)
class AuditRow:
    """A valid/test image and its closest training image."""

    split: str
    dataset: str
    dist: int
    image: Path
    closest_train: Path
    same_group: bool


def _train_index(items: Sequence[Item]) -> list[int]:
    return [k for k, item in enumerate(items) if item.split == "train"]


def _train_stack(fps: Fingerprints, train: Sequence[int]) -> NDArray[np.bool_]:
    if not train:
        raise ValueError("no training images")
    return np.stack([fps[k][0] for k in train])


def audit(items: Sequence[Item], fps: Fingerprints) -> list[AuditRow]:
    """For every valid/test item, find the closest training item."""
    train = _train_index(items)
    stack = _train_stack(fps, train)
    rows: list[AuditRow] = []
    for k, item in enumerate(items):
        if item.split == "train":
            continue
        d = distances(fps[k], stack)
        j = int(d.argmin())
        closest = items[train[j]]
        rows.append(
            AuditRow(
                split=item.split,
                dataset=item.dataset,
                dist=int(d[j]),
                image=item.path,
                closest_train=closest.path,
                same_group=item.group == closest.group,
            )
        )
    return rows


def reference_distances(items: Sequence[Item], fps: Fingerprints) -> list[int]:
    """For each training item, the distance to the closest training item of another scene.

    This is the baseline: how close two genuinely different training photos usually are.
    """
    train = _train_index(items)
    stack = _train_stack(fps, train)
    groups = np.array([items[k].group for k in train])
    out: list[int] = []
    for k in train:
        other = groups != items[k].group
        if other.any():
            out.append(int(distances(fps[k], stack)[other].min()))
    return out


def copies_to_drop(
    items: Sequence[Item], fps: Fingerprints, max_dist: int, same_labels: bool = False
) -> dict[str, str]:
    """Training images within ``max_dist`` of a valid/test image.

    Returns ``{normalised train path: split of the first valid/test image it copies}``. With
    ``same_labels`` a pair only counts when both images have exactly the same labels.
    """
    train = _train_index(items)
    stack = _train_stack(fps, train)
    drop: dict[str, str] = {}
    for k, item in enumerate(items):
        if item.split == "train":
            continue
        for j in np.flatnonzero(distances(fps[k], stack) <= max_dist):
            candidate = items[train[int(j)]]
            if same_labels and sorted(candidate.labels) != sorted(item.labels):
                continue
            drop.setdefault(path_key(candidate.path), item.split)
    return drop


def path_key(path: Path) -> str:
    """Case- and separator-normalised path, for matching manifest rows on Windows."""
    return os.path.normcase(os.path.normpath(str(path)))


def mark_dropped(
    rows: Iterable[MutableMapping[str, str]],
    root: Path,
    drop: Mapping[str, str],
    note: str,
) -> int:
    """Set ``role = leak_dropped`` on every ``keep`` row whose image is in ``drop``.

    ``note`` may contain ``{split}``, replaced by the split of the copied image.
    Returns the number of rows changed.
    """
    changed = 0
    for r in rows:
        rel = r.get("processed_rel_path") or r["rel_path"]
        key = path_key(root / rel)
        if key in drop and r["role"] == "keep":
            r["role"] = "leak_dropped"
            r["clean_note"] = note.format(split=drop[key])
            changed += 1
    return changed
