"""Trained food recogniser behind the ``FoodRecognizer`` protocol (PyTorch, CPU by default).

PyTorch and torchvision are imported only when a recogniser is built, so the service and its
tests run without them (``RECOGNIZER=mock``). The weights come from a *model bundle*, made
from a Stage 2 run by ``python -m c1_training.export`` (see ``training/README.md``): a
``torch.save`` file holding the architecture name, the weights, the class names, the input
size and the decision threshold. The bundle is loaded with ``weights_only=True``, so it cannot
run code. Weights are never committed to git.

The scores are model outputs for research use. They are not shown to patients (team rule).
"""

import threading
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from c1_food_nutrition.ml.bundle import (
    BUNDLE_FORMAT,
    REQUIRED_KEYS,
    ModelBundleError,
    build_network,
)
from c1_food_nutrition.ml.inference_input import prepare_input
from c1_food_nutrition.ml.interfaces import BgrImage, RecognizedFood
from c1_food_nutrition.ml.labels import ClassFood, foods_for, load_class_foods


class TorchFoodRecognizer:
    """Multi-label recogniser: every class scoring at least ``threshold`` is returned."""

    def __init__(
        self,
        bundle_path: Path,
        *,
        threshold: float | None = None,
        device: str = "cpu",
        class_foods: dict[str, ClassFood] | None = None,
    ) -> None:
        """Load and check the bundle.

        Args:
            bundle_path: model bundle file.
            threshold: overrides the threshold stored in the bundle (0 to 1).
            device: ``cpu`` (default for the server) or ``cuda``.
            class_foods: class to table entry; default is ``ml/data/class_concepts.csv``.

        Raises:
            ModelBundleError: the file is unreadable or inconsistent.
            UnmappedClassError: a model class is not in the class map.
            UnreviewedClassError: a model class has no reviewed food match.
        """
        try:
            import torch  # type: ignore[import-not-found, unused-ignore]
        except ImportError as exc:
            raise RuntimeError(
                "RECOGNIZER=torch needs PyTorch and torchvision in this environment "
                "(see training/README.md); use RECOGNIZER=mock otherwise."
            ) from exc
        if not bundle_path.is_file():
            raise ModelBundleError(f"model file not found: {bundle_path}")
        try:
            bundle = torch.load(bundle_path, map_location="cpu", weights_only=True)
        except Exception as exc:
            raise ModelBundleError(f"cannot read {bundle_path}: {exc}") from exc
        if not isinstance(bundle, dict):
            raise ModelBundleError(f"{bundle_path} is not a model bundle")
        missing = [k for k in REQUIRED_KEYS if k not in bundle]
        if missing:
            raise ModelBundleError(
                f"{bundle_path} lacks {missing}; export it with c1_training.export"
            )
        if bundle["format"] != BUNDLE_FORMAT:
            raise ModelBundleError(f"unknown bundle format {bundle['format']!r}")
        classes = [str(c) for c in bundle["classes"]]
        if not classes or len(set(classes)) != len(classes):
            raise ModelBundleError("bundle classes are empty or repeated")
        size = int(bundle["size"])
        chosen = float(bundle["threshold"] if threshold is None else threshold)
        if size < 32 or not 0.0 <= chosen <= 1.0:
            raise ModelBundleError(f"bad size {size} or threshold {chosen}")

        self._foods = foods_for(classes, class_foods or load_class_foods())
        net = build_network(str(bundle["arch"]), len(classes))
        try:
            net.load_state_dict(bundle["state"])
        except RuntimeError as exc:
            raise ModelBundleError(
                f"weights do not fit the {bundle['arch']} network: {exc}"
            ) from exc
        self._model = net.to(device).eval()
        self._torch = torch
        self._device = device
        self._classes = classes
        self._size = size
        self._threshold = chosen
        self._arch = str(bundle["arch"])
        self._version = str(bundle.get("run") or bundle_path.stem)
        self._lock = threading.Lock()

    @property
    def model_name(self) -> str:
        """Architecture, for ``meta.model_name``."""
        return f"{self._arch}-multilabel"

    @property
    def model_version(self) -> str:
        """The training run the weights came from, for ``meta.model_version``."""
        return self._version

    @property
    def is_mock(self) -> bool:
        """Always false: the scores come from a trained model."""
        return False

    @property
    def classes(self) -> list[str]:
        """Class names in output order."""
        return list(self._classes)

    @property
    def threshold(self) -> float:
        """Minimum score for a class to be reported."""
        return self._threshold

    @property
    def input_size(self) -> int:
        """Side of the square input, in pixels."""
        return self._size

    def class_scores(self, image: BgrImage) -> NDArray[np.float32]:
        """Sigmoid score of every class, in :attr:`classes` order."""
        torch = self._torch
        x = torch.from_numpy(prepare_input(image, self._size)).unsqueeze(0).to(self._device)
        with self._lock, torch.inference_mode():
            scores = torch.sigmoid(self._model(x))[0].float().cpu().numpy()
        out: NDArray[np.float32] = scores.astype(np.float32)
        return out

    def _food(self, label: str, score: float) -> RecognizedFood:
        entry = self._foods[label]
        note = None
        if entry.is_approximate:
            note = (
                f"'{label}': nutrition from table entry {entry.food_id} "
                f"({entry.match} match: {entry.note})"
            )
        return RecognizedFood(label, score, food_code=entry.food_id, match_note=note)

    def recognize(self, image: BgrImage) -> list[RecognizedFood]:
        """Every class scoring at least the threshold, best first (possibly none)."""
        scores = self.class_scores(image)
        order = np.argsort(-scores, kind="stable")
        return [
            self._food(self._classes[j], float(scores[j]))
            for j in order
            if scores[j] >= self._threshold
        ]
