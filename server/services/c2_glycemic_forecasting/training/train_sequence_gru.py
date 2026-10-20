"""Train a sequence GRU for four-hour CGMacros glucose forecasting.

Inputs per meal:
- eight genuine Libre readings from the ~120 minutes before the meal, oldest first, each
  with its minutes before the meal (shape 8 x 2), from build_sequence_dataset.py;
- five meal nutrition values: calories, carbs, protein, fat, fibre.

Output: sixteen glucose values at +15 ... +240 minutes.

Architecture: GRU(2 -> 32) over the history; its final hidden state is concatenated with the
nutrition values and passed through Linear(37 -> 32), ReLU, Linear(32 -> 16).
All normalisation statistics come from the training split. The checkpoint with the lowest
validation MAE is kept. The single-step model in train_gru.py is unchanged.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import Tensor, nn
from torch.utils.data import DataLoader, TensorDataset

HISTORY_LENGTH = 8
GLUCOSE_COLUMNS = tuple(f"history_glucose_{step}" for step in range(1, HISTORY_LENGTH + 1))
MINUTES_COLUMNS = tuple(f"history_minutes_before_{step}" for step in range(1, HISTORY_LENGTH + 1))
NUTRITION_COLUMNS = ("calories", "carbs", "protein", "fat", "fiber")
TARGET_COLUMNS = tuple(f"libre_gl_t{minutes:03d}" for minutes in range(15, 241, 15))

SEED = 42
HIDDEN_SIZE = 32
HEAD_SIZE = 32
BATCH_SIZE = 32
MAX_EPOCHS = 200
PATIENCE = 20
LEARNING_RATE = 0.001
OUTPUT_FILES = (
    "sequence_gru_best.pt",
    "sequence_gru_metrics.json",
    "sequence_gru_horizon_metrics.csv",
)


@dataclass
class SequenceData:
    history: np.ndarray  # (meals, 8, 2): glucose mg/dL, minutes before meal
    nutrition: np.ndarray  # (meals, 5)
    targets: np.ndarray  # (meals, 16) mg/dL
    participant_ids: set[str]


class SequenceGlucoseGRU(nn.Module):
    """Predict 16 future glucose values from a glucose history and meal nutrition."""

    def __init__(self, hidden_size: int = HIDDEN_SIZE, head_size: int = HEAD_SIZE) -> None:
        super().__init__()
        self.gru = nn.GRU(input_size=2, hidden_size=hidden_size, batch_first=True)
        self.head = nn.Sequential(
            nn.Linear(hidden_size + len(NUTRITION_COLUMNS), head_size),
            nn.ReLU(),
            nn.Linear(head_size, len(TARGET_COLUMNS)),
        )

    def forward(self, history: Tensor, nutrition: Tensor) -> Tensor:
        _, final_hidden = self.gru(history)
        predictions: Tensor = self.head(torch.cat([final_hidden[-1], nutrition], dim=1))
        return predictions


def read_sequences(path: Path, expected_split: str) -> SequenceData:
    """Read one split file, refusing rows from any other split or missing values."""
    df = pd.read_csv(path, dtype={"participant_id": str})
    required = ["participant_id", "split", *GLUCOSE_COLUMNS, *MINUTES_COLUMNS]
    required += [*NUTRITION_COLUMNS, *TARGET_COLUMNS]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    if df.empty:
        raise ValueError(f"No data rows found in {path}")
    if (df["split"] != expected_split).any():
        raise ValueError(f"{path} contains rows that are not in the {expected_split} split.")

    numeric = df[required[2:]].to_numpy(dtype=np.float32)
    if not np.isfinite(numeric).all():
        raise ValueError(f"{path} contains missing or non-finite values.")

    minutes = df[list(MINUTES_COLUMNS)].to_numpy(dtype=np.float32)
    if (minutes <= 0).any() or (np.diff(minutes, axis=1) >= 0).any():
        raise ValueError(f"{path} has history readings at/after the meal or out of order.")

    history = np.stack([df[list(GLUCOSE_COLUMNS)].to_numpy(dtype=np.float32), minutes], axis=2)
    return SequenceData(
        history=history,
        nutrition=df[list(NUTRITION_COLUMNS)].to_numpy(dtype=np.float32),
        targets=df[list(TARGET_COLUMNS)].to_numpy(dtype=np.float32),
        participant_ids=set(df["participant_id"]),
    )


def fit_normalization(train: SequenceData) -> dict[str, np.ndarray]:
    """Mean and standard deviation of every input and target, from training data only."""

    def stats(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return values.mean(axis=0), np.maximum(values.std(axis=0), 1e-6)

    # One mean/std per history channel, shared across the eight time steps.
    history_mean, history_std = stats(train.history.reshape(-1, 2))
    nutrition_mean, nutrition_std = stats(train.nutrition)
    target_mean, target_std = stats(train.targets)
    return {
        "history_mean": history_mean,
        "history_std": history_std,
        "nutrition_mean": nutrition_mean,
        "nutrition_std": nutrition_std,
        "target_mean": target_mean,
        "target_std": target_std,
    }


def normalized_inputs(data: SequenceData, norm: dict[str, np.ndarray]) -> tuple[Tensor, Tensor]:
    history = (data.history - norm["history_mean"]) / norm["history_std"]
    nutrition = (data.nutrition - norm["nutrition_mean"]) / norm["nutrition_std"]
    return torch.from_numpy(history.astype(np.float32)), torch.from_numpy(
        nutrition.astype(np.float32)
    )


def predict(
    model: SequenceGlucoseGRU, data: SequenceData, norm: dict[str, np.ndarray]
) -> np.ndarray:
    """Return predictions in mg/dL."""
    model.eval()
    history, nutrition = normalized_inputs(data, norm)
    with torch.no_grad():
        normalized = model(history, nutrition).numpy()
    predictions: np.ndarray = normalized * norm["target_std"] + norm["target_mean"]
    return predictions


def calculate_metrics(predictions: np.ndarray, actual: np.ndarray) -> dict[str, float]:
    """Mean absolute error and root mean squared error in mg/dL."""
    errors = predictions - actual
    return {
        "mae_mg_dl": float(np.mean(np.abs(errors))),
        "rmse_mg_dl": float(np.sqrt(np.mean(errors**2))),
    }


def train(
    train_csv: Path,
    validation_csv: Path,
    output_dir: Path,
    max_epochs: int = MAX_EPOCHS,
    seed: int = SEED,
) -> dict[str, Any]:
    """Train on the training split, select by validation MAE, and save the results."""
    existing = [name for name in OUTPUT_FILES if (output_dir / name).exists()]
    if existing:
        raise FileExistsError(f"{output_dir} already contains {existing}; choose a new directory.")

    train_data = read_sequences(train_csv, "train")
    validation_data = read_sequences(validation_csv, "validation")
    overlap = train_data.participant_ids & validation_data.participant_ids
    if overlap:
        raise ValueError(f"Participant leakage between training and validation: {sorted(overlap)}")

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)

    norm = fit_normalization(train_data)
    train_history, train_nutrition = normalized_inputs(train_data, norm)
    train_targets = torch.from_numpy(
        ((train_data.targets - norm["target_mean"]) / norm["target_std"]).astype(np.float32)
    )
    loader = DataLoader(
        TensorDataset(train_history, train_nutrition, train_targets),
        batch_size=BATCH_SIZE,
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
    )

    model = SequenceGlucoseGRU()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    loss_function = nn.MSELoss()

    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / "sequence_gru_best.pt"
    best_mae = float("inf")
    best_epoch = 0
    epochs_without_improvement = 0

    for epoch in range(1, max_epochs + 1):
        model.train()
        for history, nutrition, targets in loader:
            optimizer.zero_grad()
            loss = loss_function(model(history, nutrition), targets)
            loss.backward()
            optimizer.step()

        validation_metrics = calculate_metrics(
            predict(model, validation_data, norm), validation_data.targets
        )
        if validation_metrics["mae_mg_dl"] < best_mae:
            best_mae = validation_metrics["mae_mg_dl"]
            best_epoch = epoch
            epochs_without_improvement = 0
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "normalization": {k: torch.from_numpy(v) for k, v in norm.items()},
                    "history_columns": [GLUCOSE_COLUMNS, MINUTES_COLUMNS],
                    "nutrition_columns": NUTRITION_COLUMNS,
                    "target_columns": TARGET_COLUMNS,
                    "hidden_size": HIDDEN_SIZE,
                    "head_size": HEAD_SIZE,
                    "best_epoch": best_epoch,
                    "seed": seed,
                },
                checkpoint_path,
            )
        else:
            epochs_without_improvement += 1

        if epoch == 1 or epoch % 10 == 0:
            print(
                f"Epoch {epoch:03d} | Validation MAE: {validation_metrics['mae_mg_dl']:.2f} mg/dL"
                f" | Validation RMSE: {validation_metrics['rmse_mg_dl']:.2f} mg/dL"
            )
        if epochs_without_improvement >= PATIENCE:
            print(f"Early stopping at epoch {epoch}.")
            break

    best = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model.load_state_dict(best["model_state_dict"])
    predictions = predict(model, validation_data, norm)

    horizon_metrics = [
        {
            "horizon_minutes": int(column.removeprefix("libre_gl_t")),
            **calculate_metrics(predictions[:, index], validation_data.targets[:, index]),
        }
        for index, column in enumerate(TARGET_COLUMNS)
    ]
    results: dict[str, Any] = {
        "model": "Sequence GRU",
        "architecture": (
            f"GRU(2->{HIDDEN_SIZE}) over 8 history steps; final hidden state + 5 nutrition "
            f"values -> Linear({HIDDEN_SIZE + 5}->{HEAD_SIZE}) -> ReLU -> Linear({HEAD_SIZE}->16)"
        ),
        "input_shapes": {"history": [HISTORY_LENGTH, 2], "nutrition": [len(NUTRITION_COLUMNS)]},
        "output_shape": [len(TARGET_COLUMNS)],
        "config": {
            "seed": seed,
            "hidden_size": HIDDEN_SIZE,
            "head_size": HEAD_SIZE,
            "batch_size": BATCH_SIZE,
            "max_epochs": max_epochs,
            "patience": PATIENCE,
            "learning_rate": LEARNING_RATE,
            "optimizer": "Adam",
            "loss": "MSE on training-normalised targets",
            "device": "cpu",
        },
        "training_rows": len(train_data.targets),
        "training_participants": len(train_data.participant_ids),
        "validation_rows": len(validation_data.targets),
        "validation_participants": len(validation_data.participant_ids),
        "best_epoch": best_epoch,
        "validation_metrics": calculate_metrics(predictions, validation_data.targets),
        "validation_horizon_metrics": horizon_metrics,
        "note": (
            "Validation results are for model selection, not final unseen-test performance. "
            "Research prediction only; not clinically validated."
        ),
    }

    (output_dir / "sequence_gru_metrics.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    with (output_dir / "sequence_gru_horizon_metrics.csv").open(
        "w", encoding="utf-8", newline=""
    ) as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["horizon_minutes", "mae_mg_dl", "rmse_mg_dl"])
        writer.writeheader()
        writer.writerows(horizon_metrics)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the C2 sequence GRU.")
    parser.add_argument("--train-csv", type=Path, required=True)
    parser.add_argument("--validation-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-epochs", type=int, default=MAX_EPOCHS)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    results = train(
        args.train_csv, args.validation_csv, args.output_dir, args.max_epochs, args.seed
    )
    metrics = results["validation_metrics"]
    print(f"\nBest epoch: {results['best_epoch']}")
    print(f"Validation MAE: {metrics['mae_mg_dl']:.2f} mg/dL")
    print(f"Validation RMSE: {metrics['rmse_mg_dl']:.2f} mg/dL")
    print(f"Saved results to: {args.output_dir}")


if __name__ == "__main__":
    main()
