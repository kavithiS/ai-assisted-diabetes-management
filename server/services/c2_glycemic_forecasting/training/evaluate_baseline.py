from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path.home() / "Desktop" / "CGMacros_C2_processed" / "splits"

SPLITS = {
    "train": DATA_DIR / "cgmacros_train.csv",
    "validation": DATA_DIR / "cgmacros_validation.csv",
    "test": DATA_DIR / "cgmacros_test.csv",
}

BASELINE_COLUMN = "premeal_libre_gl"
TARGET_COLUMNS = [f"libre_gl_t{t:03d}" for t in range(15, 241, 15)]


def evaluate_split(name: str, path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    if not path.exists():
        raise FileNotFoundError(f"{name} dataset not found: {path}")

    df = pd.read_csv(path)

    required_columns = ["participant_id", BASELINE_COLUMN, *TARGET_COLUMNS]
    missing_columns = [column for column in required_columns if column not in df.columns]

    if missing_columns:
        raise ValueError(f"{name} dataset is missing columns: {missing_columns}")

    if df.empty:
        raise ValueError(f"{name} dataset contains no meal samples.")

    if df[required_columns].isna().any().any():
        raise ValueError(f"{name} dataset contains missing required values.")

    glucose_columns = [BASELINE_COLUMN, *TARGET_COLUMNS]

    if not all(pd.api.types.is_numeric_dtype(df[column]) for column in glucose_columns):
        raise ValueError(f"{name} dataset contains non-numeric glucose values.")

    glucose_values = df[glucose_columns].to_numpy(dtype=float)

    if not np.isfinite(glucose_values).all():
        raise ValueError(f"{name} dataset contains non-finite glucose values.")

    # Repeat the pre-meal glucose value across all 16 future time points.
    actual = df[TARGET_COLUMNS].to_numpy(dtype=float)
    predicted = np.repeat(
        df[BASELINE_COLUMN].to_numpy(dtype=float)[:, np.newaxis],
        len(TARGET_COLUMNS),
        axis=1,
    )

    errors = predicted - actual

    # Overall metrics across all meals and future time points.
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))

    # Calculate MAE separately for every forecast horizon.
    mae_by_time = np.mean(np.abs(errors), axis=0)

    participant_count = int(df["participant_id"].nunique())

    print(f"\n{name.upper()} RESULTS")
    print(f"Meal samples: {len(df)}")
    print(f"Participants: {participant_count}")
    print(f"Overall MAE: {mae:.2f} mg/dL")
    print(f"Overall RMSE: {rmse:.2f} mg/dL")
    print("\nMAE by forecast horizon:")

    horizon_results = []

    for minutes, horizon_mae in zip(range(15, 241, 15), mae_by_time, strict=True):
        horizon_mae_value = float(horizon_mae)

        print(f"  +{minutes:3d} minutes: {horizon_mae_value:.2f} mg/dL")

        horizon_results.append(
            {
                "split": name,
                "horizon_minutes": minutes,
                "mae_mg_dl": horizon_mae_value,
            }
        )

    summary = {
        "split": name,
        "meal_samples": len(df),
        "participants": participant_count,
        "mae_mg_dl": mae,
        "rmse_mg_dl": rmse,
    }

    return summary, horizon_results


def main() -> None:
    summary_results = []
    horizon_results = []

    # Evaluate training and validation only during model development.
    # Keep the test set untouched until final evaluation.
    for name in ("train", "validation"):
        summary, horizons = evaluate_split(name, SPLITS[name])
        summary_results.append(summary)
        horizon_results.extend(horizons)

    summary_df = pd.DataFrame(summary_results)
    horizon_df = pd.DataFrame(horizon_results)

    summary_path = DATA_DIR / "baseline_metrics.csv"
    horizon_path = DATA_DIR / "baseline_horizon_metrics.csv"

    summary_df.to_csv(summary_path, index=False)
    horizon_df.to_csv(horizon_path, index=False)

    print(f"\nSummary saved to: {summary_path}")
    print(f"Horizon metrics saved to: {horizon_path}")
    print("\nBaseline evaluation completed.")


if __name__ == "__main__":
    main()
