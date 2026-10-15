"""Change the labels of single images in the manifest, from a CSV of decisions.

The CSV has the columns ``image`` (the processed copy path, e.g.
``_processed/food_detect/ab12.jpg``, or the original ``rel_path``), ``old_labels`` and
``new_labels`` (both ``|``-separated), and optionally ``reason``. ``old_labels`` must match
what the manifest holds now, so a stale decision file cannot overwrite newer work.

Only the ``classes`` column and ``clean_note`` change; no image file is touched. Dry run by
default; ``--apply`` backs up the manifest first. Run in the training environment::

    python -m c1_training.relabel --changes <file.csv>
    python -m c1_training.relabel --changes <file.csv> --apply

After relabelling, re-run the leak audit and the baselines (``docs/tasks/``).
"""

import argparse
import csv
import datetime as dt
import shutil
import sys
from collections.abc import MutableMapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .manifest import read_rows, write_rows
from .paths import data_paths


class RelabelError(ValueError):
    """A decision does not match the manifest."""


@dataclass(frozen=True, slots=True)
class Change:
    """One image and its new labels."""

    image: str
    old: tuple[str, ...]
    new: tuple[str, ...]
    reason: str = ""


def split_labels(text: str) -> tuple[str, ...]:
    """``"a|b"`` to ``("a", "b")``; an empty string gives no labels."""
    return tuple(part for part in text.split("|") if part)


def read_changes(path: Path) -> list[Change]:
    """Read the decision CSV; raises :class:`RelabelError` on a missing column."""
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = {"image", "old_labels", "new_labels"} - set(reader.fieldnames or [])
        if missing:
            raise RelabelError(f"{path}: missing columns {sorted(missing)}")
        return [
            Change(
                image=row["image"].replace("\\", "/"),
                old=split_labels(row["old_labels"]),
                new=split_labels(row["new_labels"]),
                reason=row.get("reason", "") or "",
            )
            for row in reader
        ]


def apply_changes(
    rows: Sequence[MutableMapping[str, str]], changes: Sequence[Change], note: str
) -> int:
    """Set ``classes`` on the matching rows in place; returns the number of rows changed.

    Raises:
        RelabelError: an image is not in the manifest, appears twice, has no new label, or
            its current labels differ from ``old_labels``. Nothing is changed in that case.
    """
    index: dict[str, MutableMapping[str, str]] = {}
    for r in rows:
        for key in (r.get("processed_rel_path", ""), r["rel_path"]):
            if key:
                index.setdefault(key.replace("\\", "/"), r)
    seen: set[str] = set()
    plan: list[tuple[MutableMapping[str, str], Change]] = []
    for c in changes:
        row = index.get(c.image)
        if row is None:
            raise RelabelError(f"image not in the manifest: {c.image}")
        if c.image in seen:
            raise RelabelError(f"image listed twice: {c.image}")
        seen.add(c.image)
        if not c.new:
            raise RelabelError(f"no new label for {c.image}")
        if sorted(split_labels(row["classes"])) != sorted(c.old):
            raise RelabelError(
                f"{c.image}: manifest has {row['classes']!r}, decision expects {'|'.join(c.old)!r}"
            )
        plan.append((row, c))
    changed = 0
    for row, c in plan:
        if sorted(c.old) != sorted(c.new):
            row["classes"] = "|".join(c.new)
            row["clean_note"] = f"{note} ({c.reason})" if c.reason else note
            changed += 1
    return changed


def main(argv: Sequence[str] | None = None) -> int:
    """Run the relabelling; returns a process exit code."""
    p = argparse.ArgumentParser(description="Relabel manifest images from a decision CSV.")
    p.add_argument("--data-dir", default=None, help="the 'Images Datasets' folder")
    p.add_argument("--changes", type=Path, required=True, help="decision CSV")
    p.add_argument("--apply", action="store_true", help="write the manifest (default: dry run)")
    a = p.parse_args(argv)

    paths = data_paths(a.data_dir)
    manifest = paths.manifest()
    fields, rows = read_rows(manifest)
    today = dt.date.today().isoformat()
    try:
        changed = apply_changes(rows, read_changes(a.changes), f"relabelled by owner {today}")
    except RelabelError as exc:
        print(f"Nothing written: {exc}", file=sys.stderr)
        return 1
    print(f"manifest rows changed: {changed}")
    if not a.apply:
        print("Dry run. Nothing written. Add --apply to write.")
        return 0
    backup = manifest.with_name(f"{manifest.stem}_before_relabel_{today}.csv")
    if backup.exists():
        print(f"Backup already exists, not overwriting: {backup}", file=sys.stderr)
        return 1
    shutil.copy2(manifest, backup)
    write_rows(manifest, fields, rows)
    print("backup ->", backup)
    print("written ->", manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
