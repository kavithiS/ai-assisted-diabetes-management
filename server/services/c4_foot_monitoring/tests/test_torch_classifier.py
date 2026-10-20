"""Runs only where PyTorch is installed (``uv sync --all-packages --extra model``); skipped in CI.

The weights here are random. They test loading, not the model's quality.
"""

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


def _random_state() -> dict[str, object]:
    network = build_network(torch.nn, torchvision.models)
    return dict(network.state_dict())


def _save_checkpoint(path: Path, class_names: list[str] | None) -> Path:
    """Saved the way the training notebook does: weights plus class names."""
    checkpoint: dict[str, object] = {"model_state_dict": _random_state()}
    if class_names is not None:
        checkpoint["class_names"] = class_names
    torch.save(checkpoint, path)
    return path


def test_loads_plain_state_dict_with_configured_classes(tmp_path: Path, jpeg_bytes: bytes) -> None:
    weights = tmp_path / "best_resnet50_dfu.pth"
    torch.save(_random_state(), weights)
    image = decode_image(jpeg_bytes)
    assert image is not None

    classifier = TorchFootClassifier(weights, ("ulcer", "normal"))
    result = classifier.classify(image)

    assert classifier.is_mock is False
    assert classifier.model_version.startswith("best_resnet50_dfu-")
    assert result.label in {"ulcer", "normal"}
    assert 0.5 <= result.confidence <= 1.0


def test_reads_class_order_from_checkpoint(tmp_path: Path) -> None:
    weights = _save_checkpoint(tmp_path / "model.pt", ["normal", "ulcer"])

    classifier = TorchFootClassifier(weights)

    assert classifier._classes == ("normal", "ulcer")


def test_configured_classes_must_agree_with_checkpoint(tmp_path: Path) -> None:
    weights = _save_checkpoint(tmp_path / "model.pt", ["normal", "ulcer"])

    with pytest.raises(ModelLoadError, match="differs"):
        TorchFootClassifier(weights, ("ulcer", "normal"))


def test_unknown_class_order_raises(tmp_path: Path) -> None:
    weights = _save_checkpoint(tmp_path / "model.pt", None)

    with pytest.raises(ModelLoadError, match="FOOT_MODEL_CLASSES"):
        TorchFootClassifier(weights)


def test_wrong_architecture_raises(tmp_path: Path) -> None:
    weights = tmp_path / "other.pth"
    torch.save(torchvision.models.resnet18(weights=None).state_dict(), weights)

    with pytest.raises(ModelLoadError):
        TorchFootClassifier(weights, ("ulcer", "normal"))
