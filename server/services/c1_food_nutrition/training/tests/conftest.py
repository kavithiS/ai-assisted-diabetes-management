"""Fixtures for the c1_training tests.

Every image here is a SYNTHETIC TEST FIXTURE generated on the fly. Nothing is a food photo.
"""

import csv
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

MANIFEST_FIELDS = [
    "image_id",
    "dataset",
    "rel_path",
    "suggested_split",
    "classes",
    "group_id",
    "role",
    "clean_note",
    "processed_rel_path",
]

RowFactory = Callable[..., dict[str, str]]
ManifestWriter = Callable[[Path, Sequence[dict[str, str]]], Path]
PatternFactory = Callable[..., NDArray[np.uint8]]


def make_row(
    image_id: str,
    *,
    split: str = "train",
    classes: str = "rice",
    group: str | None = None,
    dataset: str = "food_detect",
    role: str = "keep",
    processed: str = "",
) -> dict[str, str]:
    """One manifest row with sensible defaults."""
    return {
        "image_id": image_id,
        "dataset": dataset,
        "rel_path": f"raw/{dataset}/{image_id}.png",
        "suggested_split": split,
        "classes": classes,
        "group_id": group or f"{dataset}:{image_id}",
        "role": role,
        "clean_note": "",
        "processed_rel_path": processed,
    }


@pytest.fixture
def row() -> RowFactory:
    """Factory for manifest rows."""
    return make_row


def _write_manifest(path: Path, rows: Sequence[dict[str, str]]) -> Path:
    """Write rows with the test columns."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _pattern(seed: int, height: int = 48, width: int = 64) -> NDArray[np.uint8]:
    """A smooth random RGB pattern: distinct seeds give clearly different pictures."""
    rng = np.random.default_rng(seed)
    coarse = rng.integers(0, 256, size=(4, 4, 3)).astype(np.float64)
    ys = np.linspace(0, 3, height)
    xs = np.linspace(0, 3, width)
    y0, x0 = np.floor(ys).astype(int).clip(0, 2), np.floor(xs).astype(int).clip(0, 2)
    fy, fx = (ys - y0)[:, None, None], (xs - x0)[None, :, None]
    a = coarse[y0][:, x0]
    b = coarse[y0][:, x0 + 1]
    c = coarse[y0 + 1][:, x0]
    d = coarse[y0 + 1][:, x0 + 1]
    img = (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
    out: NDArray[np.uint8] = img.clip(0, 255).astype(np.uint8)
    return out


@pytest.fixture
def write_manifest() -> ManifestWriter:
    """Writes manifest rows to a CSV and returns its path."""
    return _write_manifest


@pytest.fixture
def pattern() -> PatternFactory:
    """Factory for synthetic RGB patterns (``seed, height, width``)."""
    return _pattern
