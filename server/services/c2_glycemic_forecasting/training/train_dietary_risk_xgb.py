"""Train and evaluate the C2 XGBoost post-meal response classifier.

Target: `above_180_within_4h` from build_dietary_risk_labels.py, a research-defined post-meal
hyperglycaemic response indicator (not a clinically validated risk category).

Inputs: pre-meal glucose, meal nutrition and features of the deployed single-step GRU forecast
(trajectory_features.py). Observed post-meal glucose is used only for labels.

Protocol, fixed before the validation set is used:

1. Primary data: labelled, isolated meals (no other logged meal within four hours either side).
2. Hyperparameters come from a small fixed grid, scored by pooled out-of-fold average precision
   under participant-grouped K-fold cross-validation on the training participants only.
3. The decision threshold maximises F1 on the selected configuration's out-of-fold probabilities.
4. The deployed model is the all-feature XGBoost refit on all primary training meals. The
   nutrition-only XGBoost, the "GRU predicted peak > 180" rule and the no-skill rate are
   comparators and do not change which model is deployed.
5. Validation participants are scored once. Test participants are never loaded.

Known limitation: the GRU was trained on these training participants, so its training-set
forecasts are in-sample. Its error there (MAE 24.08 mg/dL) is close to its validation error
(MAE 24.91 mg/dL), but trajectory features on training meals may still be slightly optimistic.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from numpy.typing import NDArray

from c2_glycemic_forecasting import model as gru_model
from c2_glycemic_forecasting.trajectory_features import (
    FEATURE_NAMES,
    NUTRITION_FEATURES,
    build_feature_row,
)

LOGGER = logging.getLogger(__name__)

DATA_ROOT = Path.home() / "Desktop" / "CGMacros_C2_processed_premeal_fix"
CLEAN_FILE = DATA_ROOT / "cgmacros_meal_samples_clean.csv"
LABEL_FILE = DATA_ROOT / "dietary_risk_labels" / "dietary_risk_labels.csv"
OUTPUT_DIR = DATA_ROOT / "results_dietary_risk_xgb"
MODEL_FILE = "dietary_risk_xgb.json"
METADATA_FILE = "dietary_risk_xgb_metadata.json"
OUTPUT_FILES = (
    MODEL_FILE,
    METADATA_FILE,
    "metrics.json",
    "cv_results.csv",
    "validation_predictions.csv",
)

LABEL = "above_180_within_4h"
THRESHOLD_MG_DL = 180.0
SEED = 42
N_FOLDS = 5
GRID: dict[str, Sequence[Any]] = {
    "max_depth": (2, 3, 4),
    "num_boost_round": (100, 300),
    "min_child_weight": (1, 5),
}
FIXED_PARAMS: dict[str, Any] = {
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "eta": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "tree_method": "hist",
    "nthread": 1,
    "seed": SEED,
}
FEATURE_SETS = {"all_features": FEATURE_NAMES, "nutrition_only": NUTRITION_FEATURES}
DEPLOYED_FEATURE_SET = "all_features"

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


# --- metrics ------------------------------------------------------------------------------


def roc_auc(labels: IntArray, scores: FloatArray) -> float:
    """Area under the ROC curve (Mann-Whitney statistic, ties count one half)."""
    positives = scores[labels == 1]
    negatives = scores[labels == 0]
    if positives.size == 0 or negatives.size == 0:
        return float("nan")
    greater = (positives[:, None] > negatives[None, :]).sum()
    ties = (positives[:, None] == negatives[None, :]).sum()
    return float((greater + 0.5 * ties) / (positives.size * negatives.size))


def average_precision(labels: IntArray, scores: FloatArray) -> float:
    """Average precision: precision at each distinct threshold, weighted by the recall gained."""
    total_positive = int(labels.sum())
    if total_positive == 0:
        return float("nan")
    result = 0.0
    previous_recall = 0.0
    for threshold in np.unique(scores)[::-1]:
        predicted = scores >= threshold
        true_positive = int((predicted & (labels == 1)).sum())
        recall = true_positive / total_positive
        precision = true_positive / int(predicted.sum())
        result += (recall - previous_recall) * precision
        previous_recall = recall
    return float(result)


def classification_metrics(labels: IntArray, predicted: IntArray) -> dict[str, float | int]:
    """Confusion counts with precision, recall, specificity and F1 (NaN when undefined)."""
    tp = int(((predicted == 1) & (labels == 1)).sum())
    fp = int(((predicted == 1) & (labels == 0)).sum())
    fn = int(((predicted == 0) & (labels == 1)).sum())
    tn = int(((predicted == 0) & (labels == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    specificity = tn / (tn + fp) if tn + fp else float("nan")
    f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else float("nan")
    return {
        "n": int(labels.size),
        "positives": int(labels.sum()),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,
    }


def score_metrics(labels: IntArray, scores: FloatArray, threshold: float) -> dict[str, Any]:
    metrics: dict[str, Any] = classification_metrics(labels, (scores >= threshold).astype(np.int64))
    metrics["roc_auc"] = roc_auc(labels, scores)
    metrics["average_precision"] = average_precision(labels, scores)
    metrics["threshold"] = threshold
    return metrics


def best_f1_threshold(labels: IntArray, scores: FloatArray) -> float:
    """Lowest score threshold with the highest F1 among the observed scores."""
    best_threshold, best_f1 = 0.5, -1.0
    for threshold in np.unique(scores):
        f1 = classification_metrics(labels, (scores >= threshold).astype(np.int64))["f1"]
        if f1 > best_f1:
            best_threshold, best_f1 = float(threshold), float(f1)
    return best_threshold


# --- cross-validation ---------------------------------------------------------------------


def participant_folds(participants: Sequence[str], n_folds: int, seed: int) -> list[list[str]]:
    """Assign participants to folds deterministically: sort, shuffle with `seed`, round-robin."""
    unique = sorted(set(participants))
    if len(unique) < n_folds:
        raise ValueError(f"Need at least {n_folds} participants, found {len(unique)}.")
    order = np.random.default_rng(seed).permutation(len(unique))
    folds: list[list[str]] = [[] for _ in range(n_folds)]
    for position, index in enumerate(order):
        folds[position % n_folds].append(unique[index])
    return [sorted(fold) for fold in folds]


def grid_configurations() -> list[dict[str, Any]]:
    keys = list(GRID)
    return [dict(zip(keys, values, strict=True)) for values in itertools.product(*GRID.values())]


def fit_booster(features: pd.DataFrame, labels: IntArray, config: dict[str, Any]) -> xgb.Booster:
    params = {**FIXED_PARAMS, **{k: v for k, v in config.items() if k != "num_boost_round"}}
    matrix = xgb.DMatrix(features, label=labels, feature_names=list(features.columns))
    return xgb.train(params, matrix, num_boost_round=int(config["num_boost_round"]))


def predict_booster(booster: xgb.Booster, features: pd.DataFrame) -> FloatArray:
    matrix = xgb.DMatrix(features, feature_names=list(features.columns))
    return np.asarray(booster.predict(matrix), dtype=np.float64)


def out_of_fold_scores(
    features: pd.DataFrame,
    labels: IntArray,
    participants: pd.Series,
    folds: list[list[str]],
    config: dict[str, Any],
) -> FloatArray:
    scores = np.full(labels.size, np.nan)
    for fold in folds:
        held_out = participants.isin(fold).to_numpy()
        if held_out.all() or not held_out.any():
            raise ValueError("Each fold must hold out some, but not all, participants.")
        booster = fit_booster(features.loc[~held_out], labels[~held_out], config)
        scores[held_out] = predict_booster(booster, features.loc[held_out])
    return scores


def select_configuration(
    features: pd.DataFrame, labels: IntArray, participants: pd.Series, folds: list[list[str]]
) -> tuple[dict[str, Any], float, FloatArray, pd.DataFrame]:
    """Return the best configuration by out-of-fold average precision, with its threshold."""
    rows = []
    best: tuple[float, dict[str, Any], FloatArray] | None = None
    for config in grid_configurations():
        scores = out_of_fold_scores(features, labels, participants, folds, config)
        ap = average_precision(labels, scores)
        rows.append({**config, "oof_average_precision": ap, "oof_roc_auc": roc_auc(labels, scores)})
        if best is None or ap > best[0]:
            best = (ap, config, scores)
    assert best is not None
    _, config, scores = best
    return config, best_f1_threshold(labels, scores), scores, pd.DataFrame(rows)


# --- data ---------------------------------------------------------------------------------


def load_meals(clean_file: Path, label_file: Path) -> pd.DataFrame:
    """Join clean meals with their labels. Only train and validation meals are kept."""
    clean = pd.read_csv(clean_file, dtype={"participant_id": str})
    labels = pd.read_csv(label_file, dtype={"participant_id": str})
    clean = clean.loc[clean["split"].isin(("train", "validation"))]
    meals = clean.merge(
        labels.drop(columns="split"),
        on=["participant_id", "meal_timestamp"],
        how="inner",
        validate="one_to_one",
    )
    if len(meals) != len(clean):
        raise ValueError("Every clean train/validation meal must have exactly one label row.")
    mixed = meals.groupby("participant_id")["split"].nunique()
    if (mixed > 1).any():
        raise ValueError("A participant appears in more than one split.")
    return meals


def add_features(meals: pd.DataFrame) -> pd.DataFrame:
    """Add the GRU forecast features. Inputs are pre-meal glucose and nutrition only."""
    rows = []
    columns = ["premeal_libre_gl", "calories", "carbs", "protein", "fat", "fiber"]
    for values in meals[columns].to_numpy(dtype=float):
        premeal, calories, carbs, protein, fat, fiber = (float(value) for value in values)
        predictions = gru_model.predict_glucose([premeal, calories, carbs, protein, fat, fiber])
        rows.append(build_feature_row(premeal, calories, carbs, protein, fat, fiber, predictions))
    features = pd.DataFrame(rows, index=meals.index)
    # Nutrition columns are replaced by the identical values the API would compute.
    return meals.drop(columns=[c for c in features.columns if c in meals.columns]).join(features)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- main ---------------------------------------------------------------------------------


def run(
    clean_file: Path, label_file: Path, output_dir: Path, overwrite: bool = False
) -> dict[str, Any]:
    existing = [name for name in OUTPUT_FILES if (output_dir / name).exists()]
    if existing and not overwrite:
        raise FileExistsError(f"{output_dir} already contains {', '.join(existing)}.")

    meals = add_features(load_meals(clean_file, label_file))
    train = meals.loc[(meals["split"] == "train") & meals["primary_eligible"]].reset_index(
        drop=True
    )
    validation_all = meals.loc[(meals["split"] == "validation") & meals["label_valid"]]
    validation = validation_all.loc[validation_all["isolated_meal"]].reset_index(drop=True)
    preceded = validation_all.loc[~validation_all["isolated_meal"]].reset_index(drop=True)

    y_train = train[LABEL].to_numpy(dtype=np.int64)
    y_validation = validation[LABEL].to_numpy(dtype=np.int64)
    folds = participant_folds(train["participant_id"].tolist(), N_FOLDS, SEED)

    metrics: dict[str, Any] = {"cross_validation": {}, "validation": {}}
    cv_tables = []
    boosters: dict[str, xgb.Booster] = {}
    thresholds: dict[str, float] = {}
    configs: dict[str, dict[str, Any]] = {}
    validation_scores: dict[str, FloatArray] = {}

    for name, columns in FEATURE_SETS.items():
        x_train = train[list(columns)]
        config, threshold, oof, table = select_configuration(
            x_train, y_train, train["participant_id"], folds
        )
        cv_tables.append(table.assign(feature_set=name))
        metrics["cross_validation"][name] = {
            "selected_configuration": config,
            "oof_metrics_at_selected_threshold": score_metrics(y_train, oof, threshold),
        }
        boosters[name] = fit_booster(x_train, y_train, config)
        thresholds[name] = threshold
        configs[name] = config
        validation_scores[name] = predict_booster(boosters[name], validation[list(columns)])
        metrics["validation"][f"xgboost_{name}"] = score_metrics(
            y_validation, validation_scores[name], threshold
        )

    gru_peak_train = train["predicted_peak_glucose"].to_numpy(dtype=np.float64)
    gru_peak_validation = validation["predicted_peak_glucose"].to_numpy(dtype=np.float64)
    metrics["cross_validation"]["gru_peak_rule"] = score_metrics(
        y_train, gru_peak_train, np.nextafter(THRESHOLD_MG_DL, np.inf)
    )
    metrics["validation"]["gru_peak_rule"] = score_metrics(
        y_validation, gru_peak_validation, np.nextafter(THRESHOLD_MG_DL, np.inf)
    )
    metrics["validation"]["no_skill_positive_rate"] = float(y_validation.mean())

    deployed = boosters[DEPLOYED_FEATURE_SET]
    deployed_columns = list(FEATURE_SETS[DEPLOYED_FEATURE_SET])
    deployed_threshold = thresholds[DEPLOYED_FEATURE_SET]
    preceded_scores = predict_booster(deployed, preceded[deployed_columns])
    metrics["sensitivity_validation_preceded_by_meal_within_4h"] = score_metrics(
        preceded[LABEL].to_numpy(dtype=np.int64), preceded_scores, deployed_threshold
    )

    predictions = validation[
        ["participant_id", "meal_timestamp", LABEL, "observed_max_glucose"]
    ].copy()
    predictions["gru_predicted_peak"] = gru_peak_validation
    for name, scores in validation_scores.items():
        predictions[f"score_{name}"] = scores
        predictions[f"predicted_{name}"] = (scores >= thresholds[name]).astype(int)
    metrics["validation_per_participant_deployed"] = [
        {
            "participant_id": participant_id,
            **classification_metrics(
                group[LABEL].to_numpy(dtype=np.int64),
                group[f"predicted_{DEPLOYED_FEATURE_SET}"].to_numpy(dtype=np.int64),
            ),
        }
        for participant_id, group in predictions.groupby("participant_id", sort=True)
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / MODEL_FILE
    deployed.save_model(model_path)
    model_hash = sha256(model_path)
    checkpoint = gru_model._checkpoint_path()
    counts = {
        "train_primary_meals": len(train),
        "train_primary_positive": int(y_train.sum()),
        "train_participants": int(train["participant_id"].nunique()),
        "validation_primary_meals": len(validation),
        "validation_primary_positive": int(y_validation.sum()),
        "validation_participants": int(validation["participant_id"].nunique()),
        "validation_participants_with_positive": int(
            validation.groupby("participant_id")[LABEL].max().sum()
        ),
        "validation_preceded_meals": len(preceded),
    }
    metadata = {
        "model_name": "XGBoost",
        "model_version": f"xgb-above180-4h-{model_hash[:8]}",
        "model_sha256": model_hash,
        "feature_names": deployed_columns,
        "decision_threshold": deployed_threshold,
        "label_name": LABEL,
        "label_definition": (
            "At least one genuine Libre reading from +15 to +240 minutes after the meal is "
            "above 180 mg/dL. Research-defined post-meal hyperglycaemic response indicator; not "
            "a clinically validated risk category."
        ),
        "evaluation_note": (
            f"Internal evaluation only: CGMacros, {counts['validation_participants']} validation "
            f"participants ({counts['validation_primary_meals']} meals). Not clinically validated."
        ),
        "selected_configuration": configs[DEPLOYED_FEATURE_SET],
        "fixed_params": FIXED_PARAMS,
        "folds": folds,
        "counts": counts,
        "gru_checkpoint": str(checkpoint),
        "gru_checkpoint_sha256": sha256(checkpoint),
        "xgboost_version": xgb.__version__,
        "clean_file": str(clean_file.resolve()),
        "label_file": str(label_file.resolve()),
    }
    metrics["counts"] = counts
    metrics["deployed"] = {
        "feature_set": DEPLOYED_FEATURE_SET,
        "model_version": metadata["model_version"],
    }

    (output_dir / METADATA_FILE).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    pd.concat(cv_tables).to_csv(output_dir / "cv_results.csv", index=False)
    predictions.to_csv(output_dir / "validation_predictions.csv", index=False)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean-file", type=Path, default=CLEAN_FILE)
    parser.add_argument("--label-file", type=Path, default=LABEL_FILE)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    metrics = run(args.clean_file, args.label_file, args.output_dir, args.overwrite)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
