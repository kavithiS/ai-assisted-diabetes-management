"""NumPy inference for the trained C2 GRU glucose forecasting model."""

from __future__ import annotations

import os
import zipfile
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float32]

# Single-step GRU (seed 42) trained on the leakage-corrected CGMacros data.
DEFAULT_CHECKPOINT = (
    Path.home()
    / "Desktop"
    / "CGMacros_C2_processed_premeal_fix"
    / "results_single_step_gru_final"
    / "gru_best.pt"
)

STORAGE_SHAPES = {
    0: (96, 6),
    1: (96, 32),
    2: (96,),
    3: (96,),
    4: (16, 32),
    5: (16,),
    6: (6,),
    7: (6,),
    8: (16,),
    9: (16,),
}

HORIZON_MINUTES = tuple(range(15, 241, 15))


def _checkpoint_path() -> Path:
    """Allow deployment to override the local checkpoint location."""
    return Path(os.environ.get("C2_GRU_CHECKPOINT", str(DEFAULT_CHECKPOINT)))


@lru_cache(maxsize=1)
def _load_parameters() -> dict[int, FloatArray]:
    """Load known float32 storages without deserializing checkpoint pickle data."""
    checkpoint = _checkpoint_path()

    if not checkpoint.is_file():
        raise FileNotFoundError(
            f"C2 GRU checkpoint not found: {checkpoint}. "
            "Set C2_GRU_CHECKPOINT to the checkpoint file path."
        )

    parameters: dict[int, FloatArray] = {}

    with zipfile.ZipFile(checkpoint) as archive:
        byteorder_path = "gru_best/byteorder"
        if byteorder_path not in archive.namelist():
            raise ValueError("Checkpoint is missing its byte-order metadata.")

        byteorder = archive.read(byteorder_path).decode("ascii").strip()
        if byteorder != "little":
            raise ValueError(f"Unsupported checkpoint byte order: {byteorder}")

        for storage_id, shape in STORAGE_SHAPES.items():
            name = f"gru_best/data/{storage_id}"
            try:
                raw = archive.read(name)
            except KeyError as error:
                raise ValueError(f"Checkpoint is missing tensor storage {storage_id}.") from error

            values = np.frombuffer(raw, dtype="<f4")
            expected_count = int(np.prod(shape))

            if values.size != expected_count:
                raise ValueError(
                    f"Invalid tensor storage {storage_id}: "
                    f"expected {expected_count} values, found {values.size}."
                )

            tensor = values.reshape(shape).copy()

            if not np.isfinite(tensor).all():
                raise ValueError(f"Tensor storage {storage_id} contains non-finite values.")

            parameters[storage_id] = tensor

    if np.any(parameters[7] <= 0) or np.any(parameters[9] <= 0):
        raise ValueError("Checkpoint normalization standard deviations must be positive.")

    return parameters


def predict_glucose(features: Sequence[float]) -> list[float]:
    """Predict glucose at 16 horizons from six meal-related input features.

    Feature order:
    premeal glucose (mg/dL), calories (kcal), carbohydrates (g),
    protein (g), fat (g), fibre (g).
    """
    values = np.asarray(features, dtype=np.float32)

    if values.shape != (6,):
        raise ValueError("Exactly six input features are required.")

    if not np.isfinite(values).all():
        raise ValueError("Input features must be finite numbers.")

    if np.any(values[1:] < 0):
        raise ValueError("Nutrition values must be non-negative.")

    parameters = _load_parameters()

    weight_ih = parameters[0]
    bias_ih = parameters[2]
    bias_hh = parameters[3]
    output_weight = parameters[4]
    output_bias = parameters[5]
    feature_mean = parameters[6]
    feature_std = parameters[7]
    target_mean = parameters[8]
    target_std = parameters[9]

    normalized = (values - feature_mean) / feature_std

    # PyTorch GRU gate order: reset, update, new.
    input_gates = normalized @ weight_ih.T + bias_ih

    # The trained model receives one timestep. Its initial hidden state is zero,
    # so recurrent weight contributions are zero, but recurrent biases remain.
    recurrent_gates = np.broadcast_to(bias_hh, input_gates.shape)

    input_reset, input_update, input_new = np.split(input_gates, 3)
    hidden_reset, hidden_update, hidden_new = np.split(recurrent_gates, 3)

    reset_gate = 1.0 / (1.0 + np.exp(-(input_reset + hidden_reset)))
    update_gate = 1.0 / (1.0 + np.exp(-(input_update + hidden_update)))
    candidate = np.tanh(input_new + reset_gate * hidden_new)

    hidden = (1.0 - update_gate) * candidate

    normalized_predictions = output_weight @ hidden + output_bias
    predictions = normalized_predictions * target_std + target_mean

    if not np.isfinite(predictions).all():
        raise RuntimeError("The GRU produced non-finite predictions.")

    return [float(value) for value in predictions]
