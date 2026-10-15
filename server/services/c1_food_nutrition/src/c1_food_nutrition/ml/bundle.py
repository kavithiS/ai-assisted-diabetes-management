"""The model-bundle format shared by the exporter (training) and the recogniser (service).

Kept free of OpenCV and of top-level PyTorch imports, so the training environment can use it.
A bundle is a ``torch.save`` dict with the keys in :data:`REQUIRED_KEYS` (and optionally
``run``, ``valid_mAP``, ``valid_micro_f1``).
"""

from typing import Any

BUNDLE_FORMAT = "c1-recognizer/v1"
SUPPORTED_ARCHS: tuple[str, ...] = ("mobilenet_v3_large", "efficientnet_v2_s")
REQUIRED_KEYS = ("format", "arch", "state", "classes", "size", "threshold")


class ModelBundleError(ValueError):
    """The model file is missing, not a bundle, or inconsistent."""


def build_network(arch: str, n_out: int) -> Any:
    """torchvision network with ``n_out`` outputs and no pretrained weights."""
    import torch.nn as nn  # type: ignore[import-not-found, unused-ignore]
    import torchvision.models as tvm  # type: ignore[import-not-found, unused-ignore]

    if arch == "mobilenet_v3_large":
        net = tvm.mobilenet_v3_large(weights=None)
    elif arch == "efficientnet_v2_s":
        net = tvm.efficientnet_v2_s(weights=None)
    else:
        raise ModelBundleError(f"unsupported arch {arch!r}; supported: {SUPPORTED_ARCHS}")
    net.classifier[-1] = nn.Linear(net.classifier[-1].in_features, n_out)
    return net
