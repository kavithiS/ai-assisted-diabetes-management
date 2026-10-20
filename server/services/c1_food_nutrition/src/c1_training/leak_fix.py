"""Leak fix: set ``role = leak_dropped`` on training photos that copy a valid/test photo.

In the training environment (see ``training/README.md``)::

    python -m c1_training.leak_fix --max-dist 30                  # dry run
    python -m c1_training.leak_fix --max-dist 30 --apply          # backs up, then writes
    python -m c1_training.leak_fix --max-dist 48 --same-labels --apply

Look at the pairs in ``leak_audit.csv`` before applying. See
``docs/tasks/leak-audit-and-fix.md``.
"""

import argparse
import collections
import datetime as dt
import shutil
import sys
from collections.abc import Sequence

from .fingerprint import fingerprint
from .leak import copies_to_drop, mark_dropped, path_key
from .manifest import SL_SETS, items_from_rows, read_rows, write_rows
from .paths import data_paths


def main(argv: Sequence[str] | None = None) -> int:
    """Run the fix; returns a process exit code."""
    p = argparse.ArgumentParser(description="Drop training copies of valid/test photos.")
    p.add_argument("--data-dir", default=None, help="the 'Images Datasets' folder")
    p.add_argument("--max-dist", type=int, default=30, help="fingerprint distance for a copy")
    p.add_argument("--min-scenes", type=int, default=5, help="same class filter as training")
    p.add_argument("--same-labels", action="store_true", help="require identical labels")
    p.add_argument("--apply", action="store_true", help="write the manifest (default: dry run)")
    a = p.parse_args(argv)

    paths = data_paths(a.data_dir)
    manifest = paths.manifest()
    fields, rows = read_rows(manifest)
    items, classes = items_from_rows(rows, paths.root, SL_SETS, a.min_scenes)
    fps = [fingerprint(i.path) for i in items]
    drop = copies_to_drop(items, fps, a.max_dist, a.same_labels)
    by = collections.Counter(i.dataset for i in items if path_key(i.path) in drop)
    n_train = sum(i.split == "train" for i in items)
    print(f"{len(items)} images, {len(classes)} classes | train copies to drop: ", end="")
    print(f"{len(drop)} of {n_train} {dict(by)}")

    today = dt.date.today().isoformat()
    same = ", same labels" if a.same_labels else ""
    note = f"near-copy of a {{split}} image (fingerprint distance <= {a.max_dist}{same}, {today})"
    changed = mark_dropped(rows, paths.root, drop, note)
    print(f"manifest rows changed: {changed}")
    if changed != len(drop):
        print("Row count does not match the copies found. Nothing written.", file=sys.stderr)
        return 1
    if not a.apply:
        print("Dry run. Nothing written. Add --apply to write.")
        return 0

    backup = manifest.with_name(f"{manifest.stem}_before_leakfix{a.max_dist}_{today}.csv")
    if backup.exists():
        print(f"Backup already exists, not overwriting: {backup}", file=sys.stderr)
        return 1
    shutil.copy2(manifest, backup)
    write_rows(manifest, fields, rows)
    print("backup ->", backup)
    print("written ->", manifest)
    after, after_classes = items_from_rows(rows, paths.root, SL_SETS, a.min_scenes)
    print(f"after: {len(after)} images, {len(after_classes)} classes")
    lost = sorted(set(classes) - set(after_classes))
    if lost:
        print(f"classes now under --min-scenes {a.min_scenes}: {lost}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
