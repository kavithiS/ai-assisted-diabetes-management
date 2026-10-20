"""Stage 1: pre-train on Food-101 so the model learns general food features first.

Split lists: the official Food-101 ``meta`` if present, else the reconstructed split in
``_curation/food101_split``. Images: the resized copies in ``_processed/food101`` if present,
else the originals. Training environment only. See ``training/README.md``::

    python -m c1_training.stage1 --epochs 1 --per-class 20 --out-dir <scratch folder>  # test
    python -m c1_training.stage1 --epochs 8                                            # full

Writes ``stage1_<arch>[_<tag>].pt`` to ``--out-dir`` (default: the ``runs`` folder of the
data folder). **Same name means overwrite**: give quick tests their own ``--out-dir``.

Known limit: there is no validation split, so the saved epoch is the one with the best
**test** top-1, which makes that number slightly optimistic.
"""

import argparse
import random
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from .model import ARCHS, build_model
from .paths import data_paths

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def read_lines(folder: Path, name: str) -> list[str]:
    """Non-empty stripped lines of ``folder/name``."""
    text = (folder / name).read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def take(lines: Sequence[str], limit: int) -> list[str]:
    """Keep at most ``limit`` images per class, in order (0 keeps all)."""
    if not limit:
        return list(lines)
    seen: dict[str, int] = {}
    out: list[str] = []
    for line in lines:
        c = line.split("/")[0]
        if seen.get(c, 0) < limit:
            out.append(line)
            seen[c] = seen.get(c, 0) + 1
    return out


class Food101Images:
    """Map-style dataset of ``<class>/<id>`` lines. Picklable for Windows workers."""

    def __init__(
        self, lines: Sequence[str], image_dir: Path, class_index: dict[str, int], transform: Any
    ):
        self.lines, self.image_dir = list(lines), image_dir
        self.class_index, self.transform = class_index, transform

    def __len__(self) -> int:
        return len(self.lines)

    def __getitem__(self, i: int) -> tuple[Any, int]:
        from PIL import Image  # type: ignore[import-not-found, unused-ignore]

        name = self.lines[i]
        with Image.open(self.image_dir / f"{name}.jpg") as im:
            img = im.convert("RGB")
        return self.transform(img), self.class_index[name.split("/")[0]]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Command-line options."""
    p = argparse.ArgumentParser(description="Stage 1: Food-101 pre-training.")
    p.add_argument("--data-dir", default=None, help="the 'Images Datasets' folder")
    p.add_argument("--out-dir", type=Path, default=None, help="where the weights go")
    p.add_argument("--tag", default="", help="suffix for the weights file name")
    p.add_argument("--arch", default="mobilenet_v3_large", choices=ARCHS)
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--per-class", type=int, default=0, help="train images per class (0 = all)")
    p.add_argument("--bs", type=int, default=32)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--size", type=int, default=224)
    p.add_argument("--workers", type=int, default=4, help="use 0 on multiprocessing errors")
    p.add_argument("--seed", type=int, default=0)
    return p.parse_args(argv)


def run(a: argparse.Namespace) -> float:
    """Train and return the best test top-1."""
    import torch  # type: ignore[import-not-found, unused-ignore]
    import torch.nn as nn  # type: ignore[import-not-found, unused-ignore]
    import torchvision.transforms as T  # type: ignore[import-not-found, unused-ignore]
    from torch.utils.data import DataLoader  # type: ignore[import-not-found, unused-ignore]

    random.seed(a.seed)
    np.random.seed(a.seed)
    torch.manual_seed(a.seed)

    paths = data_paths(a.data_dir)
    meta = paths.food101_split_dir()
    image_dir = paths.food101_image_dir()
    print("split lists:", meta, "| images:", image_dir)
    classes = read_lines(meta, "classes.txt")
    class_index = {c: i for i, c in enumerate(classes)}
    train = take(read_lines(meta, "train.txt"), a.per_class)
    test = take(read_lines(meta, "test.txt"), a.per_class // 3 if a.per_class else 0)

    norm = T.Normalize(IMAGENET_MEAN, IMAGENET_STD)
    train_tf = T.Compose(
        [
            T.RandomResizedCrop(a.size, scale=(0.5, 1)),
            T.RandomHorizontalFlip(),
            T.ColorJitter(0.2, 0.2, 0.2),
            T.ToTensor(),
            norm,
        ]
    )
    eval_tf = T.Compose([T.Resize(int(a.size * 1.14)), T.CenterCrop(a.size), T.ToTensor(), norm])
    kw: dict[str, Any] = {"num_workers": a.workers, "persistent_workers": a.workers > 0}
    train_dl = DataLoader(
        Food101Images(train, image_dir, class_index, train_tf),
        a.bs,
        shuffle=True,
        pin_memory=True,
        **kw,
    )
    test_dl = DataLoader(Food101Images(test, image_dir, class_index, eval_tf), a.bs, **kw)

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    if dev == "cuda":
        torch.backends.cudnn.benchmark = True
    print(f"device: {dev} | train {len(train)} test {len(test)} | classes {len(classes)}")
    model = build_model(a.arch, len(classes), pretrained=True).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, a.lr, total_steps=a.epochs * len(train_dl))
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.1)
    out_dir: Path = a.out_dir or paths.runs
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / (f"stage1_{a.arch}" + (f"_{a.tag}" if a.tag else "") + ".pt")
    best = 0.0
    for ep in range(a.epochs):
        model.train()
        t0 = time.time()
        for i, (x, y) in enumerate(train_dl):
            x, y = x.to(dev), y.to(dev)
            opt.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            opt.step()
            sched.step()
            if i % 200 == 0:
                print(f"  epoch {ep + 1} batch {i}/{len(train_dl)} loss {loss.item():.3f}")
        model.eval()
        correct = total = 0
        with torch.no_grad():
            for x, y in test_dl:
                correct += int((model(x.to(dev)).argmax(1).cpu() == y).sum().item())
                total += len(y)
        acc = correct / max(total, 1)
        seconds = time.time() - t0
        print(f"epoch {ep + 1}/{a.epochs} food101 top-1 = {acc:.3f}  ({seconds:.0f}s)", flush=True)
        if acc >= best:
            best = acc
            torch.save({"arch": a.arch, "state": model.state_dict()}, out)
    print("best", round(best, 3), "->", out)
    return best


def main(argv: Sequence[str] | None = None) -> None:
    """Command-line entry point."""
    run(parse_args(argv))


if __name__ == "__main__":
    main()
