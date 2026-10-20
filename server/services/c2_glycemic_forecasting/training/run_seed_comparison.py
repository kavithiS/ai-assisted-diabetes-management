"""Multi-seed comparison of the single-step and sequence GRUs on identical validation meals.

Each training run uses the unchanged training script in its own subprocess:
- single-step: train_gru.py with its SEED set before main(); model selection on the
  corrected validation file, exactly as in the existing experiment;
- sequence: train_sequence_gru.train() with the seed; model selection on its validation file.

Every selected checkpoint is then scored on the same validation meals (those with a
complete 120-minute history), in the same order, together with the unchanged persistence
baseline. Repeating seeds measures sensitivity to initialisation and training randomness;
it is not independent participant-level validation. The test split is never read.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pandas as pd

SEEDS = (42, 1, 2, 3, 4)
MODELS = ("single_step_gru", "sequence_gru")
KEYS = ["participant_id", "meal_timestamp"]
TARGET_COLUMNS = [f"libre_gl_t{minutes:03d}" for minutes in range(15, 241, 15)]
HORIZONS = list(range(15, 241, 15))
TRAINING_DIR = Path(__file__).resolve().parent


def load_script(name: str) -> ModuleType:
    """Load a sibling training script by path (the scripts are not a package)."""
    spec = importlib.util.spec_from_file_location(f"c2_{name}", TRAINING_DIR / f"{name}.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def evaluation_meals(sequence_validation: pd.DataFrame, validation: pd.DataFrame) -> pd.DataFrame:
    """Corrected validation rows for exactly the sequence-validation meals, in that order."""
    merged = sequence_validation[KEYS].merge(
        validation, on=KEYS, how="left", validate="one_to_one", indicator=True
    )
    if (merged["_merge"] != "both").any():
        missing = merged.loc[merged["_merge"] != "both", KEYS].to_dict("records")
        raise ValueError(f"Cannot evaluate every meal; missing from validation data: {missing}")
    return merged.drop(columns="_merge").reset_index(drop=True)


def score(predictions: np.ndarray, actual: np.ndarray) -> dict[str, Any]:
    """Overall and per-horizon MAE and RMSE in mg/dL."""
    errors = predictions - actual
    return {
        "mae_mg_dl": float(np.mean(np.abs(errors))),
        "rmse_mg_dl": float(np.sqrt(np.mean(errors**2))),
        "horizon_mae_mg_dl": np.mean(np.abs(errors), axis=0).tolist(),
        "horizon_rmse_mg_dl": np.sqrt(np.mean(errors**2, axis=0)).tolist(),
    }


def summarize(runs: pd.DataFrame) -> dict[str, Any]:
    """Mean and sample standard deviation across seeds, per model."""
    summary: dict[str, Any] = {}
    for model, group in runs.groupby("model"):
        horizon_mae = np.array(group["horizon_mae_mg_dl"].tolist())
        horizon_rmse = np.array(group["horizon_rmse_mg_dl"].tolist())
        summary[str(model)] = {
            "runs": len(group),
            "mae_mean": float(group["mae_mg_dl"].mean()),
            "mae_std": float(group["mae_mg_dl"].std(ddof=1)),
            "rmse_mean": float(group["rmse_mg_dl"].mean()),
            "rmse_std": float(group["rmse_mg_dl"].std(ddof=1)),
            "horizon_mae_mean": horizon_mae.mean(axis=0).tolist(),
            "horizon_mae_std": horizon_mae.std(axis=0, ddof=1).tolist(),
            "horizon_rmse_mean": horizon_rmse.mean(axis=0).tolist(),
            "horizon_rmse_std": horizon_rmse.std(axis=0, ddof=1).tolist(),
        }
    return summary


def run_worker(args: argparse.Namespace) -> None:
    """Train one model with one seed (called in a fresh subprocess)."""
    if args.worker == "single_step_gru":
        train_gru = load_script("train_gru")
        setattr(train_gru, "SEED", args.seed)  # noqa: B010 - module attribute set at runtime
        sys.argv = [
            "train_gru.py",
            "--train-csv",
            str(args.train_csv),
            "--validation-csv",
            str(args.validation_csv),
            "--output-dir",
            str(args.output_dir),
        ]
        train_gru.main()
    else:
        load_script("train_sequence_gru").train(
            args.train_csv, args.validation_csv, args.output_dir, seed=args.seed
        )


def train_in_subprocess(
    model: str, seed: int, train_csv: Path, validation_csv: Path, output_dir: Path
) -> None:
    if output_dir.exists():
        raise FileExistsError(f"Refusing to reuse {output_dir}")
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--worker", model]
    command += ["--seed", str(seed), "--train-csv", str(train_csv)]
    command += ["--validation-csv", str(validation_csv), "--output-dir", str(output_dir)]
    log = subprocess.run(command, capture_output=True, text=True, env=os.environ)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "training_log.txt").write_text(log.stdout + log.stderr, encoding="utf-8")
    if log.returncode != 0:
        raise RuntimeError(f"{model} seed {seed} failed; see {output_dir / 'training_log.txt'}")


def predict_single_step(checkpoint: Path, meals: pd.DataFrame) -> np.ndarray:
    """Predictions from a train_gru.py checkpoint, using the API's NumPy inference."""
    evaluate_gru = load_script("evaluate_gru")
    setattr(evaluate_gru, "CHECKPOINT", checkpoint)  # noqa: B010 - module attribute set at runtime
    features = meals[list(evaluate_gru.FEATURE_COLUMNS)].to_numpy(np.float32)
    predictions: np.ndarray = evaluate_gru.predict(features, evaluate_gru.load_checkpoint_arrays())
    return predictions


def predict_sequence(checkpoint: Path, sequence_csv: Path) -> np.ndarray:
    """Predictions from a train_sequence_gru.py checkpoint on the given sequence file."""
    import torch

    trainer = load_script("train_sequence_gru")
    saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
    model = trainer.SequenceGlucoseGRU(saved["hidden_size"], saved["head_size"])
    model.load_state_dict(saved["model_state_dict"])
    norm = {key: value.numpy() for key, value in saved["normalization"].items()}
    predictions: np.ndarray = trainer.predict(
        model, trainer.read_sequences(sequence_csv, "validation"), norm
    )
    return predictions


def run_comparison(data_dir: Path, output_dir: Path, seeds: tuple[int, ...]) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"{output_dir} already exists; choose a new directory.")
    if 42 not in seeds:
        raise ValueError("The seed list must include 42.")

    splits = data_dir / "splits"
    sequences = data_dir / "sequences_120min"
    inputs = {
        "single_step_gru": (splits / "cgmacros_train.csv", splits / "cgmacros_validation.csv"),
        "sequence_gru": (
            sequences / "cgmacros_sequence_train.csv",
            sequences / "cgmacros_sequence_validation.csv",
        ),
    }
    sequence_validation = pd.read_csv(inputs["sequence_gru"][1], dtype={"participant_id": str})
    validation = pd.read_csv(inputs["single_step_gru"][1], dtype={"participant_id": str})
    meals = evaluation_meals(sequence_validation, validation)
    actual = meals[TARGET_COLUMNS].to_numpy(float)
    if not np.allclose(actual, sequence_validation[TARGET_COLUMNS].to_numpy(float)):
        raise ValueError("Sequence and corrected validation targets differ.")

    output_dir.mkdir(parents=True)
    meals[KEYS].to_csv(output_dir / "evaluation_meals.csv", index=False)

    # Persistence baseline, unchanged: evaluate_baseline.evaluate_split on the same meals.
    baseline_csv = output_dir / "baseline" / "validation_evaluation_meals.csv"
    baseline_csv.parent.mkdir()
    meals.to_csv(baseline_csv, index=False)
    baseline_summary, _ = load_script("evaluate_baseline").evaluate_split(
        "validation", baseline_csv
    )
    baseline = score(
        np.repeat(meals["premeal_libre_gl"].to_numpy(float)[:, None], len(TARGET_COLUMNS), axis=1),
        actual,
    )
    if not np.isclose(baseline["mae_mg_dl"], baseline_summary["mae_mg_dl"]):
        raise ValueError("Baseline recomputation does not match evaluate_baseline.py.")

    rows: list[dict[str, Any]] = []
    predictions: dict[tuple[str, int], np.ndarray] = {}
    for model in MODELS:
        for seed in seeds:
            run_dir = output_dir / model / f"seed_{seed:03d}"
            train_in_subprocess(model, seed, *inputs[model], run_dir)
            if model == "single_step_gru":
                own = json.loads((run_dir / "gru_metrics.json").read_text(encoding="utf-8"))
                prediction = predict_single_step(run_dir / "gru_best.pt", meals)
            else:
                own = json.loads(
                    (run_dir / "sequence_gru_metrics.json").read_text(encoding="utf-8")
                )
                prediction = predict_sequence(run_dir / "sequence_gru_best.pt", inputs[model][1])
            predictions[(model, seed)] = prediction
            run = {
                "model": model,
                "seed": seed,
                "recorded_seed": own.get("seed", own.get("config", {}).get("seed")),
                "best_epoch": own["best_epoch"],
                "selection_validation_meals": own["validation_rows"],
                "selection_validation_mae_mg_dl": own["validation_metrics"]["mae_mg_dl"],
                "evaluation_meals": len(meals),
                **score(prediction, actual),
            }
            (run_dir / "run_metrics.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
            rows.append(run)

    # Reproducibility: repeat seed 42 for both models and compare predictions exactly.
    reproducible = {}
    for model in MODELS:
        repeat_dir = output_dir / "reproducibility" / model / "seed_042_repeat"
        train_in_subprocess(model, 42, *inputs[model], repeat_dir)
        if model == "single_step_gru":
            repeat = predict_single_step(repeat_dir / "gru_best.pt", meals)
        else:
            repeat = predict_sequence(repeat_dir / "sequence_gru_best.pt", inputs[model][1])
        reproducible[model] = bool(np.array_equal(repeat, predictions[(model, 42)]))

    runs = pd.DataFrame(rows)
    flat = runs.drop(columns=["horizon_mae_mg_dl", "horizon_rmse_mg_dl"])
    flat.to_csv(output_dir / "runs_overall.csv", index=False)
    pd.DataFrame(
        [
            {
                "model": r["model"],
                "seed": r["seed"],
                "horizon_minutes": h,
                "mae_mg_dl": m,
                "rmse_mg_dl": s,
            }
            for r in rows
            for h, m, s in zip(
                HORIZONS, r["horizon_mae_mg_dl"], r["horizon_rmse_mg_dl"], strict=True
            )
        ]
        + [
            {
                "model": "persistence_baseline",
                "seed": None,
                "horizon_minutes": h,
                "mae_mg_dl": m,
                "rmse_mg_dl": s,
            }
            for h, m, s in zip(
                HORIZONS, baseline["horizon_mae_mg_dl"], baseline["horizon_rmse_mg_dl"], strict=True
            )
        ]
    ).to_csv(output_dir / "runs_by_horizon.csv", index=False)

    single = runs[runs["model"] == "single_step_gru"].set_index("seed")
    sequence = runs[runs["model"] == "sequence_gru"].set_index("seed")
    sequence_better = (
        np.array(sequence.loc[list(seeds), "horizon_mae_mg_dl"].tolist())
        < np.array(single.loc[list(seeds), "horizon_mae_mg_dl"].tolist())
    ).sum(axis=0)

    summary: dict[str, Any] = {
        "seeds": list(seeds),
        "evaluation_meals": len(meals),
        "evaluation_participants": int(meals["participant_id"].nunique()),
        "persistence_baseline": baseline,
        "models": summarize(runs),
        "seeds_where_sequence_beats_single_step_by_horizon": dict(
            zip([str(h) for h in HORIZONS], sequence_better.tolist(), strict=True)
        ),
        "seeds_where_sequence_beats_single_step_overall_mae": int(
            (sequence.loc[list(seeds), "mae_mg_dl"] < single.loc[list(seeds), "mae_mg_dl"]).sum()
        ),
        "seed_42_repeat_identical_predictions": reproducible,
        "notes": [
            "All models are scored on the same validation meals in the same order.",
            "Single-step GRU checkpoints are selected on the 175-meal corrected validation "
            "file, as in the existing experiment; sequence GRU checkpoints on its 174 meals.",
            "Seed repeats measure sensitivity to initialisation and training randomness, "
            "not independent participant-level validation (7 validation participants).",
            "The test split was not read.",
        ],
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=MODELS)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--train-csv", type=Path)
    parser.add_argument("--validation-csv", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    args = parser.parse_args()

    if args.worker:
        run_worker(args)
        return

    summary = run_comparison(args.data_dir, args.output_dir, tuple(args.seeds))
    print(json.dumps({k: v for k, v in summary.items() if k != "persistence_baseline"}, indent=2))


if __name__ == "__main__":
    main()
