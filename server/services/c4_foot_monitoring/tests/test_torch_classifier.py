"""Runs only where PyTorch is installed (``uv sync --extra model``); skipped in CI."""

from pathlib import Path

import pytest

from c4_foot_monitoring.ml.preprocessing import decode_image

torch = pytest.importorskip("torch")
torchvision = pytest.importorskip("torchvision")

from c4_foot_monitoring.ml.classifier import (  # noqa: E402
    ModelLoadError,
    TorchFootClassifier,
    build_network,
)


def _save_random_weights(path: Path) -> None:
    network = build_network(torch.nn, torchvision.models)
    torch.save(network.state_dict(), path)


def test_loads_weights_and_classifies(tmp_path: Path, jpeg_bytes: bytes) -> None:
    weights = tmp_path / "best_resnet50_dfu.pth"
    _save_random_weights(weights)
    image = decode_image(jpeg_bytes)
    assert image is not None

    classifier = TorchFootClassifier(weights, ("ulcer", "normal"))
    result = classifier.classify(image)

    assert classifier.is_mock is False
    assert classifier.model_version.startswith("best_resnet50_dfu-")
    assert result.label in {"ulcer", "normal"}
    assert 0.5 <= result.confidence <= 1.0


def test_wrong_architecture_raises(tmp_path: Path) -> None:
    weights = tmp_path / "other.pth"
    torch.save(torchvision.models.resnet18(weights=None).state_dict(), weights)

    with pytest.raises(ModelLoadError):
        TorchFootClassifier(weights, ("ulcer", "normal"))
