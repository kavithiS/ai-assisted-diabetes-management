"""Build ``image_manifest_clean.csv`` from ``image_manifest.csv``. Originals are never modified.

Rows are kept; only their ``role`` changes (the old role goes to ``role_original``):

1. Files that are missing or cannot be opened -> ``missing_file`` / ``unreadable``.
2. Scene groups that sit in more than one split. The group is kept in its most protected split
   (test, then valid, then train) and the other rows -> ``leak_dropped``.

In the training environment (see ``training/README.md``)::

    python -m c1_training.cleaning [datasets ...]

Checking files is slow, so progress is saved in ``_curation/.verify_cache.json`` and the
command stops after ``--budget`` seconds; run it again to continue.
"""

import argparse
import collections
import json
import time
from collections.abc import Mapping, MutableMapping, Sequence
from pathlib import Path
from typing import Literal

from .manifest import read_rows, write_rows
from .paths import data_paths

FileStatus = Literal["ok", "missing_file", "unreadable"]
PROTECT: dict[str, int] = {"test": 3, "valid": 2, "train": 1}


def check_file(path: Path) -> FileStatus:
    """Open and fully decode an image with Pillow (training env only)."""
    if not path.exists():
        return "missing_file"
    from PIL import Image  # type: ignore[import-not-found, unused-ignore]

    try:
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            im.draft("RGB", (128, 128))  # JPEG only: fast scaled decode, still reads the file
            im.load()  # catches truncated data that verify() misses
    except Exception:
        return "unreadable"
    return "ok"


def clean_rows(
    rows: Sequence[MutableMapping[str, str]], status: Mapping[str, str]
) -> tuple[collections.Counter[str], int]:
    """Apply both fixes in place.

    ``status`` maps ``rel_path`` to a :data:`FileStatus`; rows without an entry are left as
    they are. Returns the count of changed roles and the number of leaking groups fixed.
    """
    changed: collections.Counter[str] = collections.Counter()
    for r in rows:
        r["role_original"] = r["role"]
        r["clean_note"] = ""
        if r["role"] == "keep":
            st = status.get(r["rel_path"])
            if st and st != "ok":
                r["role"] = st
                changed[st] += 1

    groups: dict[tuple[str, str], list[MutableMapping[str, str]]] = collections.defaultdict(list)
    for r in rows:
        if r["role"] == "keep":
            groups[(r["dataset"], r["group_id"])].append(r)
    leaking = 0
    for members in groups.values():
        splits = {m["suggested_split"] for m in members}
        if len(splits) > 1:
            leaking += 1
            best = max(splits, key=lambda s: PROTECT.get(s, 0))
            for m in members:
                if m["suggested_split"] != best:
                    m["role"] = "leak_dropped"
                    m["clean_note"] = f"same scene as a {best} image"
                    changed["leak_dropped"] += 1
    return changed, leaking


def main(argv: Sequence[str] | None = None) -> int:
    """Check files (with a time budget), then write the clean manifest."""
    p = argparse.ArgumentParser(description="Build image_manifest_clean.csv.")
    p.add_argument("datasets", nargs="*", help="datasets to check (default: all)")
    p.add_argument("--data-dir", default=None, help="the 'Images Datasets' folder")
    p.add_argument("--budget", type=float, default=150.0, help="seconds per run")
    a = p.parse_args(argv)

    paths = data_paths(a.data_dir)
    fields, rows = read_rows(paths.raw_manifest)
    cache_path = paths.curation / ".verify_cache.json"
    cache: dict[str, str] = (
        json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    )
    want = set(a.datasets)
    start, left = time.time(), 0
    for r in rows:
        if r["role"] != "keep" or (want and r["dataset"] not in want) or r["rel_path"] in cache:
            continue
        if time.time() - start > a.budget:
            left += 1
            continue
        cache[r["rel_path"]] = check_file(paths.root / r["rel_path"])
    cache_path.write_text(json.dumps(cache), encoding="utf-8")
    if left:
        print(f"time budget reached: {left} images still to verify. Run again.")
        return 0

    changed, leaking = clean_rows(rows, cache)
    write_rows(paths.clean_manifest, [*fields, "role_original", "clean_note"], rows)
    keep = [r for r in rows if r["role"] == "keep"]
    print("written", paths.clean_manifest)
    print(f"rows {len(rows)} | keep {len(keep)} | changed {dict(changed)} | ", end="")
    print(f"leaking groups fixed {leaking}")
    by: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for r in keep:
        by[r["dataset"]][r["suggested_split"]] += 1
    for ds, counts in sorted(by.items()):
        print(" ", ds, dict(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
