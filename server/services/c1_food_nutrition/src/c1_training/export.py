"""Turn a Stage 2 run into the model bundle that the C1 service loads.

The bundle is one ``torch.save`` file: architecture, weights, class names, input size and the
decision threshold. The threshold is chosen on the **validation** split only (the best micro-F1
over 0.05 steps; the test split is not used). Every class must have a concept id in the
service's class map, otherwise the export stops. Training environment only::

    python -m c1_training.export --run stage2_mobilenet_v3_large_imagenet_seed0_rl256

The bundle goes to ``--out`` (default: ``<run>_bundle.pt`` next to the run). It is a model
weight file: keep it out of git.
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from c1_food_nutrition.ml.bundle import BUNDLE_FORMAT
from c1_food_nutrition.ml.labels import concepts_for, load_class_concepts

from .manifest import SL_SETS, load_manifest
from .metrics import micro_f1
from .paths import data_paths

THRESHOLDS: tuple[float, ...] = tuple(round(0.05 * k, 2) for k in range(1, 20))


def choose_threshold(
    labels: NDArray[np.generic],
    scores: NDArray[np.floating],
    candidates: Sequence[float] = THRESHOLDS,
) -> tuple[float, float]:
    """Threshold with the best micro-F1 on ``labels``/``scores``; ties go to the one nearest 0.5.

    Returns ``(threshold, micro_f1)``.
    """
    best = max(
        candidates,
        key=lambda t: (round(micro_f1(labels, scores >= t), 12), -abs(t - 0.5)),
    )
    return best, micro_f1(labels, scores >= best)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Command-line options."""
    p = argparse.ArgumentParser(description="Export a Stage 2 run as a service model bundle.")
    p.add_argument("--data-dir", default=None, help="the 'Images Datasets' folder")
    p.add_argument("--run", required=True, help="run name, e.g. stage2_..._seed0_rl256")
    p.add_argument("--runs-dir", type=Path, default=None, help="folder with the run files")
    p.add_argument("--out", type=Path, default=None, help="bundle file to write")
    p.add_argument("--size", type=int, default=None, help="input size (default: from the report)")
    p.add_argument("--workers", type=int, default=0)
    return p.parse_args(argv)


def run(a: argparse.Namespace) -> dict[str, Any]:
    """Build the bundle; returns the summary that is also printed."""
    import torch  # type: ignore[import-not-found, unused-ignore]
    import torchvision.transforms as T  # type: ignore[import-not-found, unused-ignore]
    from torch.utils.data import DataLoader  # type: ignore[import-not-found, unused-ignore]

    from .model import build_model
    from .stage2 import IMAGENET_MEAN, IMAGENET_STD, MultiLabelImages, evaluate

    paths = data_paths(a.data_dir)
    runs_dir: Path = a.runs_dir or paths.runs
    checkpoint = torch.load(runs_dir / f"{a.run}.pt", map_location="cpu")
    report = json.loads((runs_dir / f"{a.run}_report.json").read_text(encoding="utf-8"))
    classes: list[str] = list(checkpoint["classes"])
    size = int(a.size or report.get("size") or 0)
    if size < 32:
        raise SystemExit("the report has no input size (older run); pass --size")
    concepts_for(classes, load_class_concepts())  # stops on an unmapped class

    items, now = load_manifest(
        paths.manifest(),
        paths.root,
        list(SL_SETS) + list(report.get("extra_datasets", [])),
        int(report["min_scenes"]),
    )
    if now != classes:
        raise SystemExit(f"the manifest now gives {len(now)} classes, the run has {len(classes)}")
    valid = [i for i in items if i.split == "valid"]
    transform = T.Compose(
        [T.Resize((size, size)), T.ToTensor(), T.Normalize(IMAGENET_MEAN, IMAGENET_STD)]
    )
    loader = DataLoader(
        MultiLabelImages(valid, {c: k for k, c in enumerate(classes)}, transform),
        32,
        num_workers=a.workers,
    )
    model = build_model(checkpoint["arch"], len(classes), pretrained=False)
    model.load_state_dict(checkpoint["state"])
    valid_map, f1_at_half, scores, labels = evaluate(model, loader, "cpu")
    threshold, f1 = choose_threshold(labels, scores)

    bundle = {
        "format": BUNDLE_FORMAT,
        "arch": checkpoint["arch"],
        "state": checkpoint["state"],
        "classes": classes,
        "size": size,
        "threshold": float(threshold),
        "run": a.run,
        "valid_mAP": float(valid_map),
        "valid_micro_f1": float(f1),
    }
    out: Path = a.out or runs_dir / f"{a.run}_bundle.pt"
    torch.save(bundle, out)
    summary = {
        "bundle": str(out),
        "run": a.run,
        "arch": checkpoint["arch"],
        "classes": len(classes),
        "size": size,
        "threshold": threshold,
        "valid_images": len(valid),
        "valid_mAP": round(valid_map, 4),
        "valid_micro_f1_at_threshold": round(f1, 4),
        "valid_micro_f1_at_0.5": round(f1_at_half, 4),
        "megabytes": round(out.stat().st_size / 1e6, 1),
    }
    print(json.dumps(summary, indent=1))
    return summary


def main(argv: Sequence[str] | None = None) -> None:
    """Command-line entry point."""
    run(parse_args(argv))


if __name__ == "__main__":
    main()
