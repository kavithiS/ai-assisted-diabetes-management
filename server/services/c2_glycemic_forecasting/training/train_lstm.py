"""Train an LSTM model for four-hour CGMacros glucose forecasting."""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path
from typing import Any

import torch
from torch import Tensor, nn
from torch.utils.data import DataLoader, TensorDataset

FEATURE_COLUMNS = (
    "premeal_libre_gl",
    "calories",
    "carbs",
    "protein",
    "fat",
    "fiber",
)

TARGET_COLUMNS = tuple(f"libre_gl_t{minutes:03d}" for minutes in range(15, 241, 15))

SEED = 42
HIDDEN_SIZE = 32
BATCH_SIZE = 32
MAX_EPOCHS = 200
PATIENCE = 20
LEARNING_RATE = 0.001


class GlucoseLSTM(nn.Module):
    """Predict 16 future glucose values from one meal's features."""

    def __init__(
        self,
        input_size: int,
        hidden_size: int,
        output_size: int,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            batch_first=True,
        )
        self.output_layer = nn.Linear(hidden_size, output_size)

    def forward(self, inputs: Tensor) -> Tensor:
        sequence_output, _ = self.lstm(inputs.unsqueeze(1))
        final_output = sequence_output[:, -1, :]
        predictions: Tensor = self.output_layer(final_output)
        return predictions


def read_dataset(path: Path) -> tuple[Tensor, Tensor, set[str]]:
    """Read input features, glucose targets, and participant IDs from a CSV."""
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {"participant_id", *FEATURE_COLUMNS, *TARGET_COLUMNS}
        available_columns = set(reader.fieldnames or [])
        missing_columns = required_columns - available_columns

        if missing_columns:
            missing_names = ", ".join(sorted(missing_columns))
            raise ValueError(f"{path} is missing required columns: {missing_names}")

        feature_rows: list[list[float]] = []
        target_rows: list[list[float]] = []
        participant_ids: set[str] = set()

        for row_number, row in enumerate(reader, start=2):
            try:
                participant_id = (row["participant_id"] or "").strip()
                if not participant_id:
                    raise ValueError("participant_id is empty")

                features = [float(row[column] or "") for column in FEATURE_COLUMNS]
                targets = [float(row[column] or "") for column in TARGET_COLUMNS]

                all_values = features + targets
                if not all(torch.isfinite(torch.tensor(value)).item() for value in all_values):
                    raise ValueError("features or targets contain non-finite values")

            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid data at {path}, CSV row {row_number}: {error}"
                ) from error

            feature_rows.append(features)
            target_rows.append(targets)
            participant_ids.add(participant_id)

    if not feature_rows:
        raise ValueError(f"No data rows found in {path}")

    return (
        torch.tensor(feature_rows, dtype=torch.float32),
        torch.tensor(target_rows, dtype=torch.float32),
        participant_ids,
    )


def calculate_metrics(predictions: Tensor, actual: Tensor) -> dict[str, float]:
    """Calculate mean absolute error and root mean squared error in mg/dL."""
    errors = predictions - actual
    mae = float(torch.mean(torch.abs(errors)).item())
    rmse = float(torch.sqrt(torch.mean(errors**2)).item())

    return {"mae_mg_dl": mae, "rmse_mg_dl": rmse}


def evaluate_model(
    model: GlucoseLSTM,
    features: Tensor,
    targets: Tensor,
    feature_mean: Tensor,
    feature_std: Tensor,
    target_mean: Tensor,
    target_std: Tensor,
) -> tuple[Tensor, Tensor]:
    """Return glucose predictions and actual values in mg/dL."""
    model.eval()

    with torch.no_grad():
        normalized_features = (features - feature_mean) / feature_std
        normalized_predictions = model(normalized_features)
        predictions = normalized_predictions * target_std + target_mean

    return predictions, targets


def main() -> None:
    """Train the model and save its checkpoint and validation metrics."""
    parser = argparse.ArgumentParser(
        description="Train and evaluate the C2 LSTM glucose forecasting model."
    )
    parser.add_argument("--train-csv", type=Path, required=True)
    parser.add_argument("--validation-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    random.seed(SEED)
    torch.manual_seed(SEED)
    device = torch.device("cpu")

    train_features, train_targets, train_ids = read_dataset(args.train_csv)
    validation_features, validation_targets, validation_ids = read_dataset(args.validation_csv)

    overlap = train_ids & validation_ids
    if overlap:
        overlapping_ids = ", ".join(sorted(overlap))
        raise ValueError(
            f"Participant leakage detected between training and validation: {overlapping_ids}"
        )

    # Calculate normalization values using training data only.
    feature_mean = train_features.mean(dim=0)
    feature_std = train_features.std(dim=0, unbiased=False).clamp_min(1e-6)
    target_mean = train_targets.mean(dim=0)
    target_std = train_targets.std(dim=0, unbiased=False).clamp_min(1e-6)

    normalized_features = (train_features - feature_mean) / feature_std
    normalized_targets = (train_targets - target_mean) / target_std

    generator = torch.Generator().manual_seed(SEED)
    train_loader = DataLoader(
        TensorDataset(normalized_features, normalized_targets),
        batch_size=BATCH_SIZE,
        shuffle=True,
        generator=generator,
    )

    model = GlucoseLSTM(
        input_size=len(FEATURE_COLUMNS),
        hidden_size=HIDDEN_SIZE,
        output_size=len(TARGET_COLUMNS),
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    loss_function = nn.MSELoss()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "lstm_best.pt"

    best_validation_mae = float("inf")
    best_epoch = 0
    epochs_without_improvement = 0

    print(f"Training rows: {len(train_features)}")
    print(f"Training participants: {len(train_ids)}")
    print(f"Validation rows: {len(validation_features)}")
    print(f"Validation participants: {len(validation_ids)}")
    print("Device: CPU")
    print("Starting LSTM training...")

    for epoch in range(1, MAX_EPOCHS + 1):
        model.train()

        for batch_features, batch_targets in train_loader:
            optimizer.zero_grad()
            predictions = model(batch_features.to(device))
            loss = loss_function(predictions, batch_targets.to(device))
            loss.backward()
            optimizer.step()

        validation_predictions, validation_actual = evaluate_model(
            model,
            validation_features,
            validation_targets,
            feature_mean,
            feature_std,
            target_mean,
            target_std,
        )
        validation_metrics = calculate_metrics(
            validation_predictions,
            validation_actual,
        )
        validation_mae = validation_metrics["mae_mg_dl"]

        if validation_mae < best_validation_mae:
            best_validation_mae = validation_mae
            best_epoch = epoch
            epochs_without_improvement = 0

            checkpoint: dict[str, Any] = {
                "model_state_dict": model.state_dict(),
                "feature_columns": FEATURE_COLUMNS,
                "target_columns": TARGET_COLUMNS,
                "feature_mean": feature_mean,
                "feature_std": feature_std,
                "target_mean": target_mean,
                "target_std": target_std,
                "hidden_size": HIDDEN_SIZE,
                "best_epoch": best_epoch,
                "validation_metrics": validation_metrics,
            }
            torch.save(checkpoint, checkpoint_path)
        else:
            epochs_without_improvement += 1

        if epoch == 1 or epoch % 10 == 0:
            print(
                f"Epoch {epoch:03d} | "
                f"Validation MAE: {validation_mae:.2f} mg/dL | "
                f"Validation RMSE: {validation_metrics['rmse_mg_dl']:.2f} mg/dL"
            )

        if epochs_without_improvement >= PATIENCE:
            print(f"Early stopping at epoch {epoch}.")
            break

    # Restore the model selected using validation MAE.
    best_checkpoint = torch.load(
        checkpoint_path,
        map_location=device,
        weights_only=True,
    )
    model.load_state_dict(best_checkpoint["model_state_dict"])

    predictions, actual = evaluate_model(
        model,
        validation_features,
        validation_targets,
        feature_mean,
        feature_std,
        target_mean,
        target_std,
    )
    overall_metrics = calculate_metrics(predictions, actual)

    results = {
        "model": "LSTM",
        "device": str(device),
        "seed": SEED,
        "training_rows": len(train_features),
        "training_participants": len(train_ids),
        "validation_rows": len(validation_features),
        "validation_participants": len(validation_ids),
        "best_epoch": best_epoch,
        "validation_metrics": overall_metrics,
        "feature_columns": FEATURE_COLUMNS,
        "target_columns": TARGET_COLUMNS,
        "note": (
            "Single-timestep LSTM using meal features; it does not use a historical "
            "glucose sequence. Validation results are for model selection, not final "
            "unseen-test performance."
        ),
    }

    metrics_path = args.output_dir / "lstm_metrics.json"
    with metrics_path.open("w", encoding="utf-8") as json_file:
        json.dump(results, json_file, indent=2)

    horizon_path = args.output_dir / "lstm_horizon_metrics.csv"
    with horizon_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["horizon_minutes", "mae_mg_dl", "rmse_mg_dl"])

        for index, column in enumerate(TARGET_COLUMNS):
            horizon_predictions = predictions[:, index]
            horizon_actual = actual[:, index]
            horizon_metrics = calculate_metrics(
                horizon_predictions.unsqueeze(1),
                horizon_actual.unsqueeze(1),
            )
            horizon_minutes = int(column.removeprefix("libre_gl_t"))

            writer.writerow(
                [
                    horizon_minutes,
                    round(horizon_metrics["mae_mg_dl"], 4),
                    round(horizon_metrics["rmse_mg_dl"], 4),
                ]
            )

    print("\nBest validation results:")
    print(f"Best epoch: {best_epoch}")
    print(f"Validation MAE: {overall_metrics['mae_mg_dl']:.2f} mg/dL")
    print(f"Validation RMSE: {overall_metrics['rmse_mg_dl']:.2f} mg/dL")
    print(f"Saved model: {checkpoint_path}")
    print(f"Saved metrics: {metrics_path}")
    print(f"Saved horizon metrics: {horizon_path}")


if __name__ == "__main__":
    main()
