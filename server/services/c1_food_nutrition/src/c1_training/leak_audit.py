"""Leak audit: how close is each validation/test photo to the closest training photo?

In the training environment (see ``training/README.md``)::

    python -m c1_training.leak_audit [--min-scenes 5] [--data-dir <Images Datasets>]

Writes ``leak_audit.csv`` (every valid/test image with its closest training image, closest
first) into ``_curation/training/`` of the data folder, or ``--out``.
"""

import argparse
import collections
import csv
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from .fingerprint import fingerprint
from .leak import AuditRow, audit, reference_distances
from .manifest import SL_SETS, load_manifest
from .paths import data_paths

THRESHOLDS = (10, 20, 30, 40)
NEAR = 30


def format_table(rows: Sequence[AuditRow]) -> list[str]:
    """Per split and dataset: count, median distance and counts at each threshold."""
    by: dict[tuple[str, str], list[int]] = collections.defaultdict(list)
    for r in rows:
        by[(r.split, "ALL")].append(r.dist)
        by[(r.split, r.dataset)].append(r.dist)
    head = f"{'group':14s}{'images':>7s}{'median':>8s}" + "".join(
        f"{'<=' + str(t):>7s}" for t in THRESHOLDS
    )
    lines = [head]
    for (split, ds), values in sorted(by.items()):
        v = np.array(values)
        counts = "".join(f"{int((v <= t).sum()):7d}" for t in THRESHOLDS)
        lines.append(f"{split + ' ' + ds:14s}{len(v):7d}{int(np.median(v)):8d}{counts}")
    return lines


def write_csv(path: Path, rows: Sequence[AuditRow]) -> None:
    """Write the audit rows, closest pairs first."""
    fields = ["split", "dataset", "dist", "image", "closest_train", "same_group"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        for r in sorted(rows, key=lambda r: r.dist):
            writer.writerow([r.split, r.dataset, r.dist, r.image, r.closest_train, r.same_group])


def main(argv: Sequence[str] | None = None) -> None:
    """Run the audit and print the summary."""
    p = argparse.ArgumentParser(description="Leak audit of the valid/test splits.")
    p.add_argument("--data-dir", default=None, help="the 'Images Datasets' folder")
    p.add_argument("--min-scenes", type=int, default=5, help="same class filter as training")
    p.add_argument("--out", type=Path, default=None, help="CSV to write")
    p.add_argument(
        "--also",
        nargs="*",
        default=[],
        help="extra datasets whose TRAIN photos are compared with the Sri Lankan valid/test",
    )
    a = p.parse_args(argv)

    paths = data_paths(a.data_dir)
    items, classes = load_manifest(
        paths.manifest(), paths.root, list(SL_SETS) + list(a.also), a.min_scenes, a.also
    )
    print(f"{len(items)} images, {len(classes)} classes (same data as the training runs)")
    fps = [fingerprint(i.path) for i in items]
    rows = audit(items, fps)
    ref = np.array(reference_distances(items, fps))

    print("\nFor each valid/test image: distance to the closest TRAINING image")
    print("\n".join(format_table(rows)))
    print(
        "\nReference, train image vs closest train image from a DIFFERENT scene: "
        f"median {int(np.median(ref))}, share <={NEAR}: {100 * (ref <= NEAR).mean():.0f}%"
    )
    test = [r for r in rows if r.split == "test"]
    if test:
        near = sum(r.dist <= NEAR for r in test)
        print(
            f"\nTEST images with a near-identical training photo (distance <= {NEAR}): "
            f"{near} of {len(test)} ({100 * near / len(test):.0f}%)"
        )
    if a.also:
        source = {i.path: i.dataset for i in items}
        extra = [r for r in rows if source[r.closest_train] in a.also]
        print(f"\nValid/test images whose closest training photo is from {', '.join(a.also)}:")
        for t in (*THRESHOLDS, 48):
            print(f"  distance <= {t}: {sum(r.dist <= t for r in extra)}")
    out = a.out or paths.curation / "training" / "leak_audit.csv"
    write_csv(out, rows)
    print("\nClosest 8 pairs:")
    for r in sorted(rows, key=lambda r: r.dist)[:8]:
        print(f"  dist {r.dist:3d} | {r.split} | {r.image.name} <-> {r.closest_train.name}")
    print("\nSaved:", out)


if __name__ == "__main__":
    main()
