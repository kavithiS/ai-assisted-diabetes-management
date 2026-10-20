"""Evaluate the trained GRU checkpoint using NumPy only."""

from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

FLOAT = NDArray[np.float32]
FLOATING = NDArray[np.floating[Any]]

DATA_ROOT = Path.home() / "Desktop" / "CGMacros_C2_processed" / "splits"
CHECKPOINT = DATA_ROOT / "gru_results" / "gru_best.pt"
VALIDATION_CSV = DATA_ROOT / "cgmacros_validation.csv"
METRICS_JSON = DATA_ROOT / "gru_results" / "gru_metrics.json"

FEATURE_COLUMNS = (
    "premeal_libre_gl",
    "calories",
    "carbs",
    "protein",
    "fat",
    "fiber",
)

TARGET_COLUMNS = tuple(f"libre_gl_t{minutes:03d}" for minutes in range(15, 241, 15))

# Storage IDs were checked against the checkpoint metadata.
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


def load_checkpoint_arrays() -> dict[int, FLOAT]:
    """Read known float32 tensor storages without deserializing pickle data."""
    arrays: dict[int, FLOAT] = {}

    with zipfile.ZipFile(CHECKPOINT) as archive:
        byteorder = archive.read("gru_best/byteorder").decode().strip()
        if byteorder != "little":
            raise ValueError(f"Unsupported checkpoint byte order: {byteorder}")

        for storage_id, shape in STORAGE_SHAPES.items():
            raw = archive.read(f"gru_best/data/{storage_id}")
            values = np.frombuffer(raw, dtype="<f4")

            if values.size != int(np.prod(shape)):
                raise ValueError(f"Unexpected element count for storage {storage_id}")

            array = values.reshape(shape).copy()

            if not np.isfinite(array).all():
                raise ValueError(f"Non-finite values in storage {storage_id}")

            arrays[storage_id] = array

    if np.any(arrays[7] <= 0) or np.any(arrays[9] <= 0):
        raise ValueError("Normalization standard deviations must be positive")

    return arrays


def read_validation_data() -> tuple[FLOAT, FLOAT]:
    """Read the six input features and sixteen target values from CSV."""
    features: list[list[float]] = []
    targets: list[list[float]] = []

    with VALIDATION_CSV.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required = set(FEATURE_COLUMNS) | set(TARGET_COLUMNS)
        missing = required - set(reader.fieldnames or [])

        if missing:
            raise ValueError(f"Validation CSV is missing columns: {sorted(missing)}")

        for row_number, row in enumerate(reader, start=2):
            try:
                feature_row = [float(row[column]) for column in FEATURE_COLUMNS]
                target_row = [float(row[column]) for column in TARGET_COLUMNS]
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid numeric value at CSV row {row_number}") from error

            if not np.isfinite(feature_row).all() or not np.isfinite(target_row).all():
                raise ValueError(f"Non-finite value at CSV row {row_number}")

            features.append(feature_row)
            targets.append(target_row)

    if not features:
        raise ValueError("Validation CSV contains no data rows")

    return (
        np.asarray(features, dtype=np.float32),
        np.asarray(targets, dtype=np.float32),
    )


def sigmoid(values: FLOATING) -> FLOATING:
    """Numerically stable sigmoid."""
    result = np.empty_like(values)
    positive = values >= 0

    result[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exp_values = np.exp(values[~positive])
    result[~positive] = exp_values / (1.0 + exp_values)

    return result


def predict(features: FLOAT, arrays: dict[int, FLOAT]) -> FLOATING:
    """Reproduce the single-timestep PyTorch GRU forward pass."""
    weight_ih = arrays[0]
    bias_ih, bias_hh = arrays[2], arrays[3]
    output_weight, output_bias = arrays[4], arrays[5]
    feature_mean, feature_std = arrays[6], arrays[7]
    target_mean, target_std = arrays[8], arrays[9]

    normalized = (features - feature_mean) / feature_std

    # PyTorch GRU gate order is reset, update, new.
    input_gates = normalized @ weight_ih.T + bias_ih

    # The model receives a single timestep and starts with zero hidden state.
    # Therefore weight_hh @ h0 is zero, but recurrent biases still contribute.
    hidden_gates = np.broadcast_to(bias_hh, input_gates.shape)

    input_reset, input_update, input_new = np.split(input_gates, 3, axis=1)
    hidden_reset, hidden_update, hidden_new = np.split(hidden_gates, 3, axis=1)

    reset_gate = sigmoid(input_reset + hidden_reset)
    update_gate = sigmoid(input_update + hidden_update)
    candidate = np.tanh(input_new + reset_gate * hidden_new)

    initial_hidden = np.zeros_like(candidate)
    hidden = (1.0 - update_gate) * candidate + update_gate * initial_hidden

    normalized_predictions = hidden @ output_weight.T + output_bias
    return normalized_predictions * target_std + target_mean


def main() -> None:
    """Evaluate NumPy predictions against the recorded validation metrics."""
    for path in (CHECKPOINT, VALIDATION_CSV, METRICS_JSON):
        if not path.is_file():
            raise FileNotFoundError(f"Required file not found: {path}")

    arrays = load_checkpoint_arrays()
    features, actual = read_validation_data()
    predictions = predict(features, arrays)

    errors = predictions - actual
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))

    with METRICS_JSON.open("r", encoding="utf-8") as metrics_file:
        saved = json.load(metrics_file)["validation_metrics"]

    print(f"Validation rows: {len(features)}")
    print(f"Prediction shape: {predictions.shape}")
    print(f"NumPy validation MAE:  {mae:.8f} mg/dL")
    print(f"NumPy validation RMSE: {rmse:.8f} mg/dL")
    print(f"Recorded validation MAE:  {saved['mae_mg_dl']:.8f} mg/dL")
    print(f"Recorded validation RMSE: {saved['rmse_mg_dl']:.8f} mg/dL")
    print(f"MAE difference:  {abs(mae - saved['mae_mg_dl']):.8f} mg/dL")
    print(f"RMSE difference: {abs(rmse - saved['rmse_mg_dl']):.8f} mg/dL")
    print()

    horizon_path = DATA_ROOT / "gru_results" / "gru_horizon_metrics.csv"

    with horizon_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        saved_horizons = list(csv.DictReader(csv_file))

    if len(saved_horizons) != len(TARGET_COLUMNS):
        raise ValueError(
            f"Expected {len(TARGET_COLUMNS)} horizon records, found {len(saved_horizons)}"
        )

    print("\nPer-horizon comparison:")
    max_mae_difference = 0.0
    max_rmse_difference = 0.0

    for index, saved_row in enumerate(saved_horizons):
        horizon_errors = errors[:, index]
        horizon_mae = float(np.mean(np.abs(horizon_errors)))
        horizon_rmse = float(np.sqrt(np.mean(horizon_errors**2)))

        mae_difference = abs(horizon_mae - float(saved_row["mae_mg_dl"]))
        rmse_difference = abs(horizon_rmse - float(saved_row["rmse_mg_dl"]))

        max_mae_difference = max(max_mae_difference, mae_difference)
        max_rmse_difference = max(max_rmse_difference, rmse_difference)

        print(
            f"{saved_row['horizon_minutes']} min | "
            f"MAE difference: {mae_difference:.8f} | "
            f"RMSE difference: {rmse_difference:.8f}"
        )

    print(f"\nMaximum per-horizon MAE difference: {max_mae_difference:.8f}")
    print(f"Maximum per-horizon RMSE difference: {max_rmse_difference:.8f}")


if __name__ == "__main__":
    main()
