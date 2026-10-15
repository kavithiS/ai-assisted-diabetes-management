"""Stage 2: fine-tune on the Sri Lankan sets (multi-label, so plates with several foods work).

Reads the processed manifest (``role == keep`` only, split by scene group). Training
environment only. See ``training/README.md``::

    python -m c1_training.stage2 --epochs 1 --min-scenes 5 --out-dir <scratch>     # quick test
    python -m c1_training.stage2 --min-scenes 5 --seed 0                           # ImageNet
    python -m c1_training.stage2 --min-scenes 5 --seed 0 --stage1 <stage1 .pt>     # Food-101

Each run writes ``<tag>.pt`` and ``<tag>_report.json`` to ``--out-dir`` (default: the
``runs`` folder of the data folder). The tag is
``stage2_<arch>_<imagenet|food101>_seed<N>`` plus ``_<--tag>`` if given. **A run with the same
tag overwrites the earlier one**, so give quick tests their own ``--out-dir`` or ``--tag``.
"""

import argparse
import json
import random
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .manifest import SL_SETS, SPLITS, Item, load_manifest, summary
from .metrics import average_precision, mean_average_precision, micro_f1
from .model import ARCHS, build_model, load_backbone
from .paths import data_paths

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


class MultiLabelImages:
    """Map-style dataset: (image tensor, 0/1 label vector). Picklable for Windows workers."""

    def __init__(self, items: Sequence[Item], class_index: dict[str, int], transform: Any):
        self.items, self.class_index, self.transform = list(items), class_index, transform

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, i: int) -> tuple[Any, Any]:
        import torch  # type: ignore[import-not-found, unused-ignore]
        from PIL import Image  # type: ignore[import-not-found, unused-ignore]

        item = self.items[i]
        y = torch.zeros(len(self.class_index))
        for c in item.labels:
            y[self.class_index[c]] = 1
        with Image.open(item.path) as im:
            img = im.convert("RGB")
        return self.transform(img), y


def evaluate(model: Any, loader: Any, device: str) -> tuple[float, float, Any, Any]:
    """Return ``(mAP, micro-F1 at 0.5, scores, labels)`` on ``loader``."""
    import torch  # type: ignore[import-not-found, unused-ignore]

    model.eval()
    scores, labels = [], []
    with torch.no_grad():
        for x, y in loader:
            scores.append(torch.sigmoid(model(x.to(device))).cpu())
            labels.append(y)
    p = torch.cat(scores).numpy()
    t = torch.cat(labels).numpy()
    return mean_average_precision(t, p), micro_f1(t, p > 0.5), p, t


def per_class_report(
    classes: Sequence[str], scores: NDArray[np.floating], labels: NDArray[np.floating]
) -> list[dict[str, Any]]:
    """AP and test positives per class that occurs in the split, weakest first."""
    rows: list[dict[str, Any]] = []
    for j, c in enumerate(classes):
        positives = int(labels[:, j].sum())
        if positives:
            ap = round(average_precision(labels[:, j], scores[:, j]), 3)
            rows.append({"class": c, "test_positives": positives, "AP": ap})
    return sorted(rows, key=lambda r: r["AP"])


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Command-line options."""
    p = argparse.ArgumentParser(description="Stage 2: multi-label fine-tuning.")
    p.add_argument("--data-dir", default=None, help="the 'Images Datasets' folder")
    p.add_argument("--out-dir", type=Path, default=None, help="where weights and report go")
    p.add_argument("--tag", default="", help="suffix for the run name")
    p.add_argument("--arch", default="mobilenet_v3_large", choices=ARCHS)
    p.add_argument("--stage1", default="", help="Stage 1 checkpoint (empty = ImageNet only)")
    p.add_argument("--no-pretrained", action="store_true", help="random start (tests only)")
    p.add_argument("--also", nargs="*", default=[], help="extra datasets: pust foodbd veg_cooking")
    p.add_argument("--min-scenes", type=int, default=1, help="drop classes with fewer scenes")
    p.add_argument("--epochs", type=int, default=15)
    p.add_argument("--bs", type=int, default=32)
    p.add_argument("--lr", type=float, default=5e-4)
    # 256 = the stored image size; it beat 224 on 5 of 5 seeds (docs/EXPERIMENTS.md, 2026-10-15)
    p.add_argument("--size", type=int, default=256)
    p.add_argument("--workers", type=int, default=4, help="use 0 on multiprocessing errors")
    p.add_argument("--seed", type=int, default=0)
    return p.parse_args(argv)


def run(a: argparse.Namespace) -> dict[str, Any]:
    """Train, pick the best epoch by valid mAP, score the test split once; return the report."""
    import torch  # type: ignore[import-not-found, unused-ignore]
    import torch.nn as nn  # type: ignore[import-not-found, unused-ignore]
    import torchvision.transforms as T  # type: ignore[import-not-found, unused-ignore]
    from torch.utils.data import DataLoader  # type: ignore[import-not-found, unused-ignore]

    random.seed(a.seed)
    np.random.seed(a.seed)
    torch.manual_seed(a.seed)

    paths = data_paths(a.data_dir)
    items, classes = load_manifest(
        paths.manifest(), paths.root, list(SL_SETS) + list(a.also), a.min_scenes
    )
    print(summary(items, classes))
    class_index = {c: i for i, c in enumerate(classes)}
    split = {s: [i for i in items if i.split == s] for s in SPLITS}

    norm = T.Normalize(IMAGENET_MEAN, IMAGENET_STD)
    train_tf = T.Compose(
        [
            T.RandomResizedCrop(a.size, scale=(0.6, 1)),
            T.RandomHorizontalFlip(),
            T.ColorJitter(0.3, 0.3, 0.3, 0.05),
            T.ToTensor(),
            norm,
        ]
    )
    eval_tf = T.Compose([T.Resize((a.size, a.size)), T.ToTensor(), norm])
    kw: dict[str, Any] = {"num_workers": a.workers, "persistent_workers": a.workers > 0}
    train_dl = DataLoader(
        MultiLabelImages(split["train"], class_index, train_tf), a.bs, shuffle=True, **kw
    )
    valid_dl = DataLoader(MultiLabelImages(split["valid"], class_index, eval_tf), a.bs, **kw)
    test_dl = DataLoader(MultiLabelImages(split["test"], class_index, eval_tf), a.bs, **kw)

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    if dev == "cuda":
        torch.backends.cudnn.benchmark = True
    print(f"device: {dev} | seed {a.seed} | stage1: {a.stage1 or 'none (ImageNet only)'}")
    model = build_model(a.arch, len(classes), pretrained=not a.stage1 and not a.no_pretrained)
    if a.stage1:
        print(f"loaded {load_backbone(model, Path(a.stage1))} backbone tensors from {a.stage1}")
    model.to(dev)

    # rare classes count more in the loss
    pos = torch.zeros(len(classes))
    for item in split["train"]:
        for c in item.labels:
            pos[class_index[c]] += 1
    pos_weight = (len(split["train"]) / pos.clamp(min=1)).clamp(max=20).sqrt().to(dev)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, a.lr, total_steps=a.epochs * len(train_dl))

    out_dir: Path = a.out_dir or paths.runs
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"stage2_{a.arch}_{'food101' if a.stage1 else 'imagenet'}_seed{a.seed}"
    if a.tag:
        tag += f"_{a.tag}"
    ckpt = out_dir / f"{tag}.pt"
    best = -1.0
    for ep in range(a.epochs):
        model.train()
        t0 = time.time()
        for x, y in train_dl:
            x, y = x.to(dev), y.to(dev)
            opt.zero_grad()
            loss_fn(model(x), y).backward()
            opt.step()
            sched.step()
        valid_map, valid_f1, _, _ = evaluate(model, valid_dl, dev)
        seconds = time.time() - t0
        print(
            f"epoch {ep + 1}/{a.epochs} valid mAP={valid_map:.3f} "
            f"microF1={valid_f1:.3f}  ({seconds:.0f}s)",
            flush=True,
        )
        if valid_map > best:
            best = valid_map
            torch.save({"arch": a.arch, "state": model.state_dict(), "classes": classes}, ckpt)

    model.load_state_dict(torch.load(ckpt, map_location=dev)["state"])
    test_map, test_f1, scores, labels = evaluate(model, test_dl, dev)
    print(f"\nTEST (held-out scenes) mAP={test_map:.3f} microF1={test_f1:.3f}")
    report: dict[str, Any] = {
        "run": tag,
        "seed": a.seed,
        "stage1": a.stage1 or None,
        "arch": a.arch,
        "epochs": a.epochs,
        "min_scenes": a.min_scenes,
        "size": a.size,
        "batch_size": a.bs,
        "lr": a.lr,
        "tag": a.tag or None,
        "extra_datasets": list(a.also),
        "n_classes": len(classes),
        "n_images": {s: len(v) for s, v in split.items()},
        "best_valid_mAP": round(best, 4),
        "test_mAP": test_map,
        "test_microF1": test_f1,
        "manifest": str(paths.manifest()),
        "per_class": per_class_report(classes, scores, labels),
    }
    out = out_dir / f"{tag}_report.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("report ->", out, "(weakest classes first)")
    return report


def main(argv: Sequence[str] | None = None) -> None:
    """Command-line entry point."""
    run(parse_args(argv))


if __name__ == "__main__":
    main()
