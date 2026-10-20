"""Model builders (PyTorch and torchvision; training environment only)."""

from pathlib import Path
from typing import Any

ARCHS: tuple[str, ...] = ("mobilenet_v3_large", "efficientnet_v2_s")


def build_model(arch: str, n_out: int, pretrained: bool = True) -> Any:
    """torchvision backbone with a new final layer of ``n_out`` outputs.

    ``pretrained`` loads the ImageNet weights (downloaded once by torchvision, about 20 MB
    for MobileNetV3-Large and 80 MB for EfficientNetV2-S).
    """
    import torch.nn as nn  # type: ignore[import-not-found, unused-ignore]
    import torchvision.models as tvm  # type: ignore[import-not-found, unused-ignore]

    weights = "DEFAULT" if pretrained else None
    if arch == "mobilenet_v3_large":
        m = tvm.mobilenet_v3_large(weights=weights)
    elif arch == "efficientnet_v2_s":
        m = tvm.efficientnet_v2_s(weights=weights)
    else:
        raise ValueError(f"unknown arch {arch!r}; choose from {ARCHS}")
    m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, n_out)
    return m


def load_backbone(model: Any, path: Path) -> int:
    """Load Stage 1 weights into ``model``, skipping tensors whose shape differs.

    The final layer has a different number of classes, so it is skipped. Returns the number
    of tensors loaded; check it (310 for MobileNetV3-Large).
    """
    import torch  # type: ignore[import-not-found, unused-ignore]

    state = torch.load(path, map_location="cpu")["state"]
    own = model.state_dict()
    keep = {k: v for k, v in state.items() if k in own and v.shape == own[k].shape}
    model.load_state_dict(keep, strict=False)
    return len(keep)
