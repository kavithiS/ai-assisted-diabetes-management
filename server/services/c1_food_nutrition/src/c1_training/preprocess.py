"""Make training-ready copies of the images. Originals are never modified.

For every ``keep`` row of ``image_manifest_clean.csv``:

* apply the EXIF rotation, so phone photos are upright;
* convert CMYK / RGBA / palette / grey to RGB (transparent areas become white);
* resize so the short side is ``--short-side`` pixels (default 256), keeping the aspect ratio;
  smaller images are not enlarged (note ``small``);
* save as JPEG (quality 92) in ``_processed/<dataset>/<hash>.jpg``.

Writes ``processed_manifest.csv`` (the clean columns plus the processed-copy columns) and
``preprocess_report.json``. Rows that ``leak_fix`` had set to ``leak_dropped`` in the previous
``processed_manifest.csv`` keep that role, so a re-run does not undo the leak fix.

In the training environment (see ``training/README.md``)::

    python -m c1_training.preprocess [--datasets a b c] [--short-side 256] [--workers 2]
"""

import argparse
import collections
import hashlib
import json
import time
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path

from .manifest import read_rows, write_rows
from .paths import data_paths

DEFAULT_DATASETS = ("food_detect", "shorteats", "sl_meal", "kaggle_sl26", "veg_cooking")
EXTRA_COLUMNS = (
    "processed_rel_path",
    "orig_w",
    "orig_h",
    "orig_mode",
    "proc_w",
    "proc_h",
    "proc_note",
    "proc_error",
)
LEAK_FIX_MARK = "fingerprint distance"


@dataclass(frozen=True, slots=True)
class Processed:
    """Result for one image; ``error`` is the exception name, or empty."""

    image_id: str
    rel_path: str
    orig_w: int
    orig_h: int
    orig_mode: str
    proc_w: int
    proc_h: int
    note: str
    error: str

    def columns(self) -> dict[str, str]:
        """Values for :data:`EXTRA_COLUMNS`."""
        values = (
            self.rel_path,
            self.orig_w,
            self.orig_h,
            self.orig_mode,
            self.proc_w,
            self.proc_h,
            self.note,
            self.error,
        )
        return {k: str(v) for k, v in zip(EXTRA_COLUMNS, values, strict=True)}


def out_rel(image_id: str, dataset: str) -> str:
    """Relative path of the processed copy (forward slashes, as in the manifest)."""
    digest = hashlib.sha1(image_id.encode("utf-8")).hexdigest()[:16]
    return f"_processed/{dataset}/{digest}.jpg"


def target_size(width: int, height: int, short: int) -> tuple[int, int, str]:
    """Size after resizing so the short side is ``short``; never enlarges.

    Returns ``(width, height, note)``; ``note`` is ``small`` when the image is smaller.
    """
    if min(width, height) > short:
        k = short / min(width, height)
        new_w, new_h = round(width * k), round(height * k)
        if width <= height:
            new_w = short
        else:
            new_h = short
        return new_w, new_h, ""
    return width, height, "small" if min(width, height) < short else ""


def process_image(src: Path, dst: Path, short: int) -> tuple[int, int, str, int, int, str]:
    """Write the processed copy of ``src`` to ``dst`` (Pillow; training env only).

    Returns ``(orig_w, orig_h, orig_mode, proc_w, proc_h, note)``.
    """
    from PIL import Image, ImageOps  # type: ignore[import-not-found, unused-ignore]

    with Image.open(src) as opened:
        mode, (ow, oh) = opened.mode, opened.size
        if opened.format == "JPEG":  # fast scaled decode, still at least the target size
            s = min(ow, oh)
            if s > short:
                k = short / s
                opened.draft("RGB", (max(1, int(ow * k)), max(1, int(oh * k))))
        im = ImageOps.exif_transpose(opened)
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            im = im.convert("RGBA")
            background = Image.new("RGB", im.size, (255, 255, 255))
            background.paste(im, mask=im.getchannel("A"))
            im = background
        else:
            im = im.convert("RGB")
        w, h = im.size
        new_w, new_h, note = target_size(w, h, short)
        if (new_w, new_h) != (w, h):
            im = im.resize((new_w, new_h), Image.LANCZOS)
        dst.parent.mkdir(parents=True, exist_ok=True)
        im.save(dst, "JPEG", quality=92)
        return ow, oh, mode, im.size[0], im.size[1], note


def _work(job: tuple[str, str, str, str, int]) -> Processed:
    image_id, dataset, src, root, short = job
    rel = out_rel(image_id, dataset)
    try:
        ow, oh, mode, pw, ph, note = process_image(Path(src), Path(root) / rel, short)
    except Exception as exc:
        return Processed(image_id, "", 0, 0, "", 0, 0, "", type(exc).__name__)
    return Processed(image_id, rel, ow, oh, mode, pw, ph, note, "")


def merge_rows(
    rows: Sequence[MutableMapping[str, str]],
    done: Mapping[str, Processed],
    previous: Mapping[str, Mapping[str, str]],
) -> list[MutableMapping[str, str]]:
    """Add the processed-copy columns to each clean row, in place.

    New results win, then the previous ``processed_manifest.csv``, then empty values. A row
    that ``leak_fix`` dropped in the previous manifest keeps ``leak_dropped`` and its note.
    """
    for r in rows:
        iid = r["image_id"]
        if iid in done:
            r.update(done[iid].columns())
        elif iid in previous:
            r.update({k: previous[iid].get(k, "") for k in EXTRA_COLUMNS})
        else:
            r.update(dict.fromkeys(EXTRA_COLUMNS, ""))
        before = previous.get(iid)
        if (
            before is not None
            and r["role"] == "keep"
            and before.get("role") == "leak_dropped"
            and LEAK_FIX_MARK in before.get("clean_note", "")
        ):
            r["role"] = "leak_dropped"
            r["clean_note"] = before["clean_note"]
    return list(rows)


def main(argv: Sequence[str] | None = None) -> int:
    """Process the images that are not done yet, then rewrite the processed manifest."""
    p = argparse.ArgumentParser(description="Make resized RGB training copies.")
    p.add_argument("--data-dir", default=None, help="the 'Images Datasets' folder")
    p.add_argument("--datasets", nargs="*", default=list(DEFAULT_DATASETS))
    p.add_argument("--short-side", type=int, default=256)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--budget", type=float, default=150.0, help="seconds per run")
    a = p.parse_args(argv)

    paths = data_paths(a.data_dir)
    fields, rows = read_rows(paths.clean_manifest)
    previous: dict[str, dict[str, str]] = {}
    if paths.processed_manifest.exists():
        previous = {r["image_id"]: r for r in read_rows(paths.processed_manifest)[1]}

    def finished(r: Mapping[str, str]) -> bool:
        rel = previous.get(r["image_id"], {}).get("processed_rel_path", "")
        return bool(rel) and (paths.root / rel).exists()

    todo = [
        r for r in rows if r["role"] == "keep" and r["dataset"] in a.datasets and not finished(r)
    ]
    print(f"{len(todo)} images to process")
    jobs = [
        (
            r["image_id"],
            r["dataset"],
            str(paths.root / r["rel_path"]),
            str(paths.root),
            a.short_side,
        )
        for r in todo
    ]
    done: dict[str, Processed] = {}
    start = time.time()
    with Pool(a.workers) as pool:
        for result in pool.imap_unordered(_work, jobs, chunksize=8):
            done[result.image_id] = result
            if time.time() - start > a.budget:
                pool.terminate()
                print("time budget reached; run again to continue")
                break

    out = merge_rows(rows, done, previous)
    write_rows(paths.processed_manifest, [*fields, *EXTRA_COLUMNS], out)
    ok = [r for r in out if r["processed_rel_path"]]
    report = {
        "short_side": a.short_side,
        "processed": len(ok),
        "errors": sum(1 for r in out if r["proc_error"]),
        "by_dataset": dict(collections.Counter(r["dataset"] for r in ok)),
        "converted_from_mode": dict(
            collections.Counter(r["orig_mode"] for r in ok if r["orig_mode"] != "RGB")
        ),
        "small_not_enlarged": sum(1 for r in ok if "small" in r["proc_note"]),
    }
    (paths.curation / "preprocess_report.json").write_text(
        json.dumps(report, indent=1), encoding="utf-8"
    )
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
