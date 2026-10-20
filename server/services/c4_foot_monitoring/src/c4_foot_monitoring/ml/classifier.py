"""Trained foot classifier: torchvision ResNet50 with a custom head (PyTorch, CPU by default).

PyTorch and torchvision are imported only when this classifier is built, so the service and
its tests run without them (mock mode). Install them with the ``model`` extra::

    uv sync --extra model   # or: uv pip install torch torchvision

The weights file (``best_resnet50_dfu.pth``) is never committed to git. It is loaded with
``weights_only=True``, so it cannot run code.

The scores are model outputs for research use. They are never shown to patients (team rule).
"""

import hashlib
import logging
import threading
from pathlib import Path
from typing import Any

import numpy as np

from c4_foot_monitoring.config import FootLabel, Settings
from c4_foot_monitoring.ml.interfaces import BgrImage, FootClassification, FootClassifier
from c4_foot_monitoring.ml.mock import MockFootClassifier
from c4_foot_monitoring.ml.preprocessing import to_model_input

logger = logging.getLogger(__name__)

MODEL_NAME = "resnet50-dfu"


class ModelLoadError(RuntimeError):
    """The weights file is missing, unreadable or does not fit the architecture."""


def build_network(torch_nn: Any, torchvision_models: Any) -> Any:
    """ResNet50 with the head used in training: 2048 â†’ 256 â†’ 2."""
    network = torchvision_models.resnet50(weights=None)
    network.fc = torch_nn.Sequential(
        torch_nn.Dropout(0.3),
        torch_nn.Linear(2048, 256),
        torch_nn.ReLU(),
        torch_nn.Dropout(0.2),
        torch_nn.Linear(256, 2),
    )
    return network


def _file_version(path: Path) -> str:
    """Short content hash of the weights, so every stored result names its exact model."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"{path.stem}-{digest.hexdigest()[:8]}"


def _classes_from(
    checkpoint_classes: object, configured: tuple[FootLabel, FootLabel] | None
) -> tuple[FootLabel, FootLabel]:
    """The class order: from the checkpoint's ``class_names``, else from the settings."""
    from_file: tuple[FootLabel, FootLabel] | None = None
    if checkpoint_classes is not None:
        if not isinstance(checkpoint_classes, list | tuple):
            raise ModelLoadError("class_names in the checkpoint is not a list")
        names = [str(name).lower() for name in checkpoint_classes]
        if sorted(names) != ["normal", "ulcer"]:
            raise ModelLoadError(f"Unexpected class_names in the checkpoint: {names}")
        from_file = ("normal", "ulcer") if names[0] == "normal" else ("ulcer", "normal")
    if from_file and configured and from_file != configured:
        raise ModelLoadError(
            f"FOOT_MODEL_CLASSES {list(configured)} differs from the checkpoint's "
            f"class_names {list(from_file)}"
        )
    classes = from_file or configured
    if classes is None:
        raise ModelLoadError(
            "The checkpoint has no class_names; set FOOT_MODEL_CLASSES to the training order"
        )
    return classes


class TorchFootClassifier:
    """Binary classifier: the class with the highest softmax score wins."""

    def __init__(
        self,
        weights_path: Path,
        classes: tuple[FootLabel, FootLabel] | None = None,
        device: str = "cpu",
    ) -> None:
        """Load the weights.

        Args:
            weights_path: a ``state_dict``, or a checkpoint dict with ``model_state_dict``
                and ``class_names`` as saved by the training notebook.
            classes: label of output index 0 and 1. Optional when the checkpoint has
                ``class_names``; if both are given they must agree.
            device: ``cpu`` (default for the server) or ``cuda``.

        Raises:
            ModelLoadError: the file is missing, does not fit the architecture, or the class
                order is unknown or contradictory.
            RuntimeError: PyTorch or torchvision is not installed.
        """
        if not weights_path.is_file():
            raise ModelLoadError(f"Model weights not found: {weights_path}")

        try:
            import torch  # type: ignore[import-not-found, import-untyped, unused-ignore]
            import torchvision  # type: ignore[import-not-found, import-untyped, unused-ignore]
        except ImportError as exc:
            raise RuntimeError(
                "FOOT_MODEL_PATH needs PyTorch and torchvision in this environment "
                "(uv sync --extra model)."
            ) from exc

        try:
            state = torch.load(weights_path, map_location=device, weights_only=True)
            checkpoint_classes = None
            if isinstance(state, dict) and "model_state_dict" in state:
                checkpoint_classes = state.get("class_names")
                state = state["model_state_dict"]
            classes = _classes_from(checkpoint_classes, classes)
            network = build_network(torch.nn, torchvision.models)
            network.load_state_dict(state)
        except ModelLoadError:
            raise
        except (OSError, RuntimeError, KeyError, ValueError) as exc:
            raise ModelLoadError(f"Could not load model weights from {weights_path}") from exc

        network.to(device)
        network.eval()
        self._torch = torch
        self._network = network
        self._device = device
        self._classes = classes
        self._version = _file_version(weights_path)
        self._lock = threading.Lock()

    @property
    def model_name(self) -> str:
        return MODEL_NAME

    @property
    def model_version(self) -> str:
        return self._version

    @property
    def is_mock(self) -> bool:
        return False

    def classify(self, image: BgrImage) -> FootClassification:
        batch = self._torch.from_numpy(to_model_input(image)).to(self._device)
        with self._lock, self._torch.inference_mode():
            logits = self._network(batch)
            probabilities = self._torch.softmax(logits, dim=1)[0].cpu().numpy()
        index = int(np.argmax(probabilities))
        return FootClassification(
            label=self._classes[index], confidence=float(probabilities[index])
        )


def build_classifier(settings: Settings) -> FootClassifier:
    """The trained classifier when configured and loadable, otherwise the mock.

    A missing weights file falls back to the mock with a warning, so the demo still runs;
    every response then says ``is_mock: true``.
    """
    if settings.foot_model_path is None:
        logger.info("FOOT_MODEL_PATH not set: using the mock foot classifier.")
        return MockFootClassifier()
    try:
        classifier = TorchFootClassifier(
            settings.foot_model_path,
            settings.foot_model_classes,
            device=settings.foot_model_device,
        )
    except ModelLoadError as exc:
        logger.warning("%s. Falling back to the mock foot classifier.", exc)
        return MockFootClassifier()
    logger.info("Foot classifier loaded: %s", classifier.model_version)
    return classifier
