"""Check that training can start: Python, PyTorch, GPU, libraries and data.

In the training environment (see ``training/README.md``)::

    python -m c1_training.check_setup
"""

import platform
import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Print one line per check; returns 1 if a required part is missing."""
    import argparse

    p = argparse.ArgumentParser(description="Check the training environment.")
    p.add_argument("--data-dir", default=None, help="the 'Images Datasets' folder")
    a = p.parse_args(argv)
    failed = False
    print(f"Python {platform.python_version()} at {sys.executable}")
    try:
        import torch  # type: ignore[import-not-found, unused-ignore]
        import torchvision  # type: ignore[import-not-found, unused-ignore]

        print(f"torch {torch.__version__} | torchvision {torchvision.__version__}")
        if torch.cuda.is_available():
            memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"GPU: YES - {torch.cuda.get_device_name(0)}, {memory:.1f} GB memory")
            x = torch.randn(256, 256, device="cuda")
            (x @ x).sum().item()
            print("GPU test calculation: OK")
        else:
            print("GPU: NO - training will run on the processor only (slow).")
    except Exception as exc:
        failed = True
        print(f"PyTorch problem: {type(exc).__name__}: {exc}")
    try:
        import numpy
        import PIL  # type: ignore[import-not-found, unused-ignore]

        print(f"numpy {numpy.__version__} | pillow {PIL.__version__}")
    except Exception as exc:
        failed = True
        print(f"Library problem: {type(exc).__name__}: {exc}")
    try:
        from .manifest import SL_SETS, load_manifest
        from .paths import data_paths

        paths = data_paths(a.data_dir)
        items, classes = load_manifest(paths.manifest(), paths.root, SL_SETS, 5)
        missing = sum(1 for i in items if not i.path.exists())
        print(f"Sri Lankan data: {len(items)} images, {len(classes)} classes, missing: {missing}")
        found = (paths.food101_split_dir() / "train.txt").is_file()
        print(f"Food-101 split lists: {'found' if found else 'MISSING'}")
    except Exception as exc:
        failed = True
        print(f"Data problem: {type(exc).__name__}: {exc}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
