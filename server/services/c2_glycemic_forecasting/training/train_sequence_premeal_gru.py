"""Train an experimental sequence GRU with a direct premeal glucose input.

Identical to train_sequence_gru.py except that the prediction head also receives the newest
genuine premeal glucose reading directly, so the model does not have to carry it through the
recurrent state. The direct input is `history_glucose_8`: the newest history reading, which
build_sequence_dataset.py guarantees equals the corrected premeal_libre_gl (strictly before
the meal). No other data source is added.

Inputs per meal: history (8, 2) [glucose mg/dL, minutes before meal], oldest first;
nutrition (5); premeal glucose (1).
Architecture: GRU(2 -> 32); [final hidden (32) + nutrition (5) + premeal (1)] = 38
-> Linear(38 -> 32) -> ReLU -> Linear(32 -> 16).
Normalisation: training split only (the premeal value has its own mean and SD).
Selection: lowest validation MAE. The existing sequence and single-step GRUs are unchanged.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import random
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import Tensor, nn
from torch.utils.data import DataLoader, TensorDataset


def _load_sequence_trainer() -> ModuleType:
    # Training scripts are standalone files, not a package, so load the sibling by path.
    path = Path(__file__).with_name("train_sequence_gru.py")
    spec = importlib.util.spec_from_file_location("c2_train_sequence_gru", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


base = _load_sequence_trainer()

PREMEAL_COLUMN = base.GLUCOSE_COLUMNS[-1]  # newest reading == corrected premeal_libre_gl
SEED = base.SEED
HIDDEN_SIZE = base.HIDDEN_SIZE
HEAD_SIZE = base.HEAD_SIZE
BATCH_SIZE = base.BATCH_SIZE
MAX_EPOCHS = base.MAX_EPOCHS
PATIENCE = base.PATIENCE
LEARNING_RATE = base.LEARNING_RATE
OUTPUT_FILES = (
    "sequence_premeal_gru_best.pt",
    "sequence_premeal_gru_metrics.json",
    "sequence_premeal_gru_horizon_metrics.csv",
    "validation_predictions.csv",
)


class SequencePremealGRU(nn.Module):
    """Sequence GRU whose head also receives the premeal glucose value directly."""

    def __init__(self, hidden_size: int = HIDDEN_SIZE, head_size: int = HEAD_SIZE) -> None:
        super().__init__()
        self.gru = nn.GRU(input_size=2, hidden_size=hidden_size, batch_first=True)
        self.head = nn.Sequential(
            nn.Linear(hidden_size + len(base.NUTRITION_COLUMNS) + 1, head_size),
            nn.ReLU(),
            nn.Linear(head_size, len(base.TARGET_COLUMNS)),
        )

    def forward(self, history: Tensor, nutrition: Tensor, premeal: Tensor) -> Tensor:
        _, final_hidden = self.gru(history)
        features = torch.cat([final_hidden[-1], nutrition, premeal], dim=1)
        predictions: Tensor = self.head(features)
        return predictions


def premeal_values(data: Any) -> np.ndarray:
    """The direct premeal input: the newest history glucose reading, shape (meals, 1)."""
    values: np.ndarray = data.history[:, -1, 0:1].astype(np.float32)
    return values


def fit_normalization(train: Any) -> dict[str, np.ndarray]:
    """Existing sequence statistics plus premeal mean/SD, all from training data only."""
    norm: dict[str, np.ndarray] = base.fit_normalization(train)
    premeal = premeal_values(train)
    norm["premeal_mean"] = premeal.mean(axis=0)
    norm["premeal_std"] = np.maximum(premeal.std(axis=0), 1e-6)
    return norm


def model_inputs(data: Any, norm: dict[str, np.ndarray]) -> tuple[Tensor, Tensor, Tensor]:
    history, nutrition = base.normalized_inputs(data, norm)
    premeal = (premeal_values(data) - norm["premeal_mean"]) / norm["premeal_std"]
    return history, nutrition, torch.from_numpy(premeal.astype(np.float32))


def predict(model: SequencePremealGRU, data: Any, norm: dict[str, np.ndarray]) -> np.ndarray:
    """Return predictions in mg/dL."""
    model.eval()
    with torch.no_grad():
        normalized = model(*model_inputs(data, norm)).numpy()
    predictions: np.ndarray = normalized * norm["target_std"] + norm["target_mean"]
    return predictions


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

    train_data = base.read_sequences(train_csv, "train")
    validation_data = base.read_sequences(validation_csv, "validation")
    overlap = train_data.participant_ids & validation_data.participant_ids
    if overlap:
        raise ValueError(f"Participant leakage between training and validation: {sorted(overlap)}")

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)

    norm = fit_normalization(train_data)
    train_targets = torch.from_numpy(
        ((train_data.targets - norm["target_mean"]) / norm["target_std"]).astype(np.float32)
    )
    loader = DataLoader(
        TensorDataset(*model_inputs(train_data, norm), train_targets),
        batch_size=BATCH_SIZE,
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
    )

    model = SequencePremealGRU()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    loss_function = nn.MSELoss()

    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / "sequence_premeal_gru_best.pt"
    best_mae = float("inf")
    best_epoch = 0
    epochs_without_improvement = 0

    for epoch in range(1, max_epochs + 1):
        model.train()
        for history, nutrition, premeal, targets in loader:
            optimizer.zero_grad()
            loss = loss_function(model(history, nutrition, premeal), targets)
            loss.backward()
            optimizer.step()

        validation_metrics = base.calculate_metrics(
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
                    "premeal_column": PREMEAL_COLUMN,
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

    validation_frame = pd.read_csv(validation_csv, dtype={"participant_id": str})
    per_meal = validation_frame[["participant_id", "meal_timestamp"]].copy()
    for index, column in enumerate(base.TARGET_COLUMNS):
        per_meal[f"prediction_{column}"] = predictions[:, index]
    per_meal.to_csv(output_dir / "validation_predictions.csv", index=False)

    horizon_metrics = [
        {
            "horizon_minutes": int(column.removeprefix("libre_gl_t")),
            **base.calculate_metrics(predictions[:, index], validation_data.targets[:, index]),
        }
        for index, column in enumerate(base.TARGET_COLUMNS)
    ]
    results: dict[str, Any] = {
        "model": "Sequence GRU with direct premeal glucose",
        "architecture": (
            f"GRU(2->{HIDDEN_SIZE}) over 8 history steps; final hidden state + 5 nutrition "
            f"values + 1 premeal glucose = {HIDDEN_SIZE + 6} -> Linear({HIDDEN_SIZE + 6}->"
            f"{HEAD_SIZE}) -> ReLU -> Linear({HEAD_SIZE}->16)"
        ),
        "input_shapes": {"history": [8, 2], "nutrition": [5], "premeal": [1]},
        "premeal_source": f"{PREMEAL_COLUMN} (equals corrected premeal_libre_gl)",
        "output_shape": [len(base.TARGET_COLUMNS)],
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
        "validation_metrics": base.calculate_metrics(predictions, validation_data.targets),
        "validation_horizon_metrics": horizon_metrics,
        "note": (
            "Validation results are for model selection, not final unseen-test performance. "
            "Research prediction only; not clinically validated."
        ),
    }
    (output_dir / "sequence_premeal_gru_metrics.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    with (output_dir / "sequence_premeal_gru_horizon_metrics.csv").open(
        "w", encoding="utf-8", newline=""
    ) as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["horizon_minutes", "mae_mg_dl", "rmse_mg_dl"])
        writer.writeheader()
        writer.writerows(horizon_metrics)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the experimental premeal sequence GRU.")
    parser.add_argument("--train-csv", type=Path, required=True)
    parser.add_argument("--validation-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[SEED])
    parser.add_argument("--max-epochs", type=int, default=MAX_EPOCHS)
    args = parser.parse_args()

    if len(args.seeds) == 1:
        targets = {args.seeds[0]: args.output_dir}
    else:
        targets = {seed: args.output_dir / f"seed_{seed:03d}" for seed in args.seeds}
    for seed, directory in targets.items():
        results = train(args.train_csv, args.validation_csv, directory, args.max_epochs, seed)
        metrics = results["validation_metrics"]
        print(
            f"Seed {seed}: best epoch {results['best_epoch']}, validation MAE "
            f"{metrics['mae_mg_dl']:.2f}, RMSE {metrics['rmse_mg_dl']:.2f} mg/dL -> {directory}"
        )


if __name__ == "__main__":
    main()
