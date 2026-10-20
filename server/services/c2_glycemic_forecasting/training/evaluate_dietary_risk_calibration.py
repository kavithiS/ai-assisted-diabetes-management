"""Evaluate the probability calibration of the deployed C2 XGBoost dietary-risk model.

Evaluation only. Nothing is trained, refitted or tuned:

- The deployed model is loaded through the service loader (`dietary_risk.load_classifier`),
  which checks its SHA-256, feature names and decision threshold. Scores come from that booster
  exactly as `estimate_above_threshold` computes them.
- Features are recomputed with the training script's `add_features` and the deployed GRU
  checkpoint. Recomputed scores must match the stored validation predictions, and the Boolean
  indicator must equal `score >= decision_threshold` for every meal.
- No calibrator (Platt, isotonic or other) is fitted. Validation labels are used only to compute
  the metrics below, once.
- Only validation participants are scored. Test participants are never loaded.
- Every file in the model results directory and the GRU checkpoint are hashed before and after
  the run; the run fails if any changed.

The written report is aggregate only. It is checked for participant identifiers, timestamps and
per-meal values before it is saved.

Caveats recorded in the report: only seven validation participants; the GRU checkpoint was
selected on validation loss, so validation is not fully untouched for this pipeline; the data are
CGMacros, not a Sri Lankan clinical cohort.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import logging
import math
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import xgboost as xgb
from numpy.typing import NDArray

LOGGER = logging.getLogger(__name__)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def _load_training_script() -> ModuleType:
    # Training scripts are standalone files, not a package, so load the sibling by path.
    path = Path(__file__).with_name("train_dietary_risk_xgb.py")
    spec = importlib.util.spec_from_file_location("c2_train_dietary_risk_xgb", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


DATA_ROOT = Path.home() / "Desktop" / "CGMacros_C2_processed_premeal_fix"
MODEL_DIR = DATA_ROOT / "results_dietary_risk_xgb"
OUTPUT_DIR = DATA_ROOT / "results_dietary_risk_calibration"
REPORT_FILE = "calibration_report.json"
STORED_PREDICTIONS = "validation_predictions.csv"
METADATA_FILE = "dietary_risk_xgb_metadata.json"

SEED = 42
BOOTSTRAP_RESAMPLES = 2000
RELIABILITY_BINS = 3
# Log loss clips predictions to [EPS, 1 - EPS]; the number of clipped values is reported.
EPS = 1e-6
SCORE_MATCH_TOLERANCE = 1e-6

# Exploratory criteria proposed in Phase A. They are not clinical or universal standards.
EXPLORATORY_SLOPE_RANGE = (0.7, 1.3)


# --- input checks -------------------------------------------------------------------------


def validate_inputs(probabilities: Any, labels: Any) -> tuple[FloatArray, IntArray]:
    """Return checked copies: equal length, non-empty, finite p in [0, 1], labels in {0, 1}."""
    p = np.asarray(probabilities, dtype=np.float64)
    y = np.asarray(labels)
    if p.ndim != 1 or y.ndim != 1 or p.size != y.size:
        raise ValueError("Probabilities and labels must be 1-D arrays of equal length.")
    if p.size == 0:
        raise ValueError("At least one prediction is required.")
    if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError("Probabilities must be finite and within [0, 1].")
    if not np.isin(y, (0, 1)).all():
        raise ValueError("Labels must be 0 or 1.")
    return p, y.astype(np.int64)


# --- metrics ------------------------------------------------------------------------------


def brier_score(probabilities: Any, labels: Any) -> float:
    p, y = validate_inputs(probabilities, labels)
    return float(np.mean((p - y) ** 2))


def brier_skill_score(probabilities: Any, labels: Any, reference_rate: float) -> float:
    """1 - Brier / Brier of a constant `reference_rate`. Above 0 means better than the constant."""
    if not 0.0 < reference_rate < 1.0:
        raise ValueError("The reference rate must be in (0, 1).")
    p, y = validate_inputs(probabilities, labels)
    reference = float(np.mean((reference_rate - y) ** 2))
    return 1.0 - brier_score(p, y) / reference


def clip_probabilities(probabilities: Any, eps: float = EPS) -> tuple[FloatArray, int]:
    p = np.asarray(probabilities, dtype=np.float64)
    clipped = np.clip(p, eps, 1 - eps)
    return clipped, int(np.count_nonzero(clipped != p))


def log_loss(probabilities: Any, labels: Any, eps: float = EPS) -> float:
    p, y = validate_inputs(probabilities, labels)
    q, _ = clip_probabilities(p, eps)
    return float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q)))


def _logit(p: FloatArray, eps: float = EPS) -> FloatArray:
    q, _ = clip_probabilities(p, eps)
    return np.asarray(np.log(q / (1 - q)), dtype=np.float64)


@dataclass(frozen=True)
class LogisticFit:
    coefficients: tuple[float, ...]
    converged: bool


def fit_logistic(
    design: FloatArray,
    labels: IntArray,
    offset: FloatArray | None = None,
    max_iterations: int = 100,
    max_abs_coefficient: float = 50.0,
) -> LogisticFit:
    """Unpenalised logistic regression by Newton-Raphson.

    Reports `converged=False` instead of returning a number when the fit diverges, as happens
    with separation or a single class.
    """
    offset = np.zeros(labels.size) if offset is None else offset
    beta = np.zeros(design.shape[1])
    for _ in range(max_iterations):
        eta = design @ beta + offset
        p = 1.0 / (1.0 + np.exp(-eta))
        weights = p * (1 - p)
        hessian = design.T @ (design * weights[:, None])
        try:
            step = np.linalg.solve(hessian, design.T @ (labels - p))
        except np.linalg.LinAlgError:
            return LogisticFit(tuple(float(b) for b in beta), False)
        beta = beta + step
        if not np.isfinite(beta).all() or np.abs(beta).max() > max_abs_coefficient:
            return LogisticFit(tuple(float(b) for b in beta), False)
        if np.abs(step).max() < 1e-10:
            return LogisticFit(tuple(float(b) for b in beta), True)
    return LogisticFit(tuple(float(b) for b in beta), False)


def calibration_intercept_slope(probabilities: Any, labels: Any) -> tuple[float, float]:
    """Calibration intercept (calibration-in-the-large) and slope on the logit scale.

    Intercept: `a` in logit(P(y=1)) = a + logit(p), with the slope fixed at 1.
    Slope: `b` in logit(P(y=1)) = a' + b * logit(p).
    Perfect calibration gives intercept 0 and slope 1. NaN means the fit did not converge or
    only one class is present.
    """
    p, y = validate_inputs(probabilities, labels)
    if y.min() == y.max():
        return math.nan, math.nan
    z = _logit(p)
    ones = np.ones((y.size, 1))
    intercept_fit = fit_logistic(ones, y, offset=z)
    slope_fit = fit_logistic(np.column_stack([np.ones(y.size), z]), y)
    intercept = intercept_fit.coefficients[0] if intercept_fit.converged else math.nan
    slope = slope_fit.coefficients[1] if slope_fit.converged else math.nan
    return float(intercept), float(slope)


def roc_auc(probabilities: Any, labels: Any) -> float:
    """Mann-Whitney ROC-AUC (ties count one half); NaN with a single class."""
    p, y = validate_inputs(probabilities, labels)
    positives, negatives = p[y == 1], p[y == 0]
    if positives.size == 0 or negatives.size == 0:
        return math.nan
    greater = (positives[:, None] > negatives[None, :]).sum()
    ties = (positives[:, None] == negatives[None, :]).sum()
    return float((greater + 0.5 * ties) / (positives.size * negatives.size))


def average_precision(probabilities: Any, labels: Any) -> float:
    """Average precision over distinct score thresholds; NaN without positives."""
    p, y = validate_inputs(probabilities, labels)
    total = int(y.sum())
    if total == 0:
        return math.nan
    result, previous_recall = 0.0, 0.0
    for threshold in np.unique(p)[::-1]:
        predicted = p >= threshold
        true_positive = int((predicted & (y == 1)).sum())
        recall = true_positive / total
        result += (recall - previous_recall) * true_positive / int(predicted.sum())
        previous_recall = recall
    return float(result)


def wilson_interval(successes: int, total: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval for a proportion (treats meals as independent)."""
    if total <= 0:
        return math.nan, math.nan
    phat = successes / total
    denominator = 1 + z**2 / total
    centre = (phat + z**2 / (2 * total)) / denominator
    half = z * math.sqrt(phat * (1 - phat) / total + z**2 / (4 * total**2)) / denominator
    return centre - half, centre + half


def reliability_table(
    probabilities: Any, labels: Any, bins: int = RELIABILITY_BINS
) -> list[dict[str, Any]]:
    """Equal-size bins by predicted probability (ties broken by input order, stably)."""
    p, y = validate_inputs(probabilities, labels)
    if bins < 1 or bins > p.size:
        raise ValueError("The number of bins must be between 1 and the number of meals.")
    order = np.argsort(p, kind="mergesort")
    table = []
    for index, chunk in enumerate(np.array_split(order, bins), start=1):
        positives = int(y[chunk].sum())
        low, high = wilson_interval(positives, chunk.size)
        table.append(
            {
                "bin": index,
                "meals": int(chunk.size),
                "positives": positives,
                "predicted_min": float(p[chunk].min()),
                "predicted_max": float(p[chunk].max()),
                "mean_predicted": float(p[chunk].mean()),
                "observed_rate": positives / chunk.size,
                "observed_rate_wilson95_meal_level": [low, high],
            }
        )
    return table


# --- participant-level uncertainty --------------------------------------------------------

Statistic = Callable[[FloatArray, IntArray], float]


def cluster_bootstrap(
    probabilities: Any,
    labels: Any,
    groups: Any,
    statistic: Statistic,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = SEED,
) -> dict[str, Any]:
    """Percentile interval from resampling whole participants with replacement.

    Resamples with a single class, or where the statistic is not finite, are skipped and
    counted rather than forced.
    """
    p, y = validate_inputs(probabilities, labels)
    group_array = np.asarray(groups)
    if group_array.size != p.size:
        raise ValueError("Groups must have one entry per prediction.")
    unique = np.unique(group_array)
    members = [np.flatnonzero(group_array == g) for g in unique]
    rng = np.random.default_rng(seed)
    values: list[float] = []
    single_class = 0
    not_finite = 0
    for _ in range(resamples):
        chosen = rng.integers(0, unique.size, unique.size)
        index = np.concatenate([members[c] for c in chosen])
        if y[index].min() == y[index].max():
            single_class += 1
            continue
        value = statistic(p[index], y[index])
        if not math.isfinite(value):
            not_finite += 1
            continue
        values.append(value)
    used = len(values)
    interval = (
        [float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))]
        if used
        else [math.nan, math.nan]
    )
    return {
        "percentile95": interval,
        "clusters": int(unique.size),
        "resamples_requested": resamples,
        "resamples_used": used,
        "skipped_single_class": single_class,
        "skipped_not_finite": not_finite,
        "seed": seed,
    }


def leave_one_participant_out(
    probabilities: Any,
    labels: Any,
    groups: Any,
    statistic: Statistic,
) -> dict[str, Any]:
    """Recompute `statistic` with each participant removed; returns anonymous summaries only."""
    p, y = validate_inputs(probabilities, labels)
    group_array = np.asarray(groups)
    if group_array.size != p.size:
        raise ValueError("Groups must have one entry per prediction.")
    values = []
    for group in np.unique(group_array):
        keep = group_array != group
        if keep.sum() == 0 or y[keep].min() == y[keep].max():
            values.append(math.nan)
            continue
        values.append(statistic(p[keep], y[keep]))
    finite = [v for v in values if math.isfinite(v)]
    return {
        "analyses": len(values),
        "not_computable": len(values) - len(finite),
        "min": min(finite) if finite else math.nan,
        "median": float(np.median(finite)) if finite else math.nan,
        "max": max(finite) if finite else math.nan,
    }


# --- evaluation ---------------------------------------------------------------------------


def evaluate(
    probabilities: Any,
    labels: Any,
    groups: Any,
    training_rate: float,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = SEED,
) -> dict[str, Any]:
    """All aggregate calibration and discrimination results for one set of predictions."""
    p, y = validate_inputs(probabilities, labels)
    group_array = np.asarray(groups)
    constant = np.full(p.size, training_rate)
    _, clipped = clip_probabilities(p)
    intercept, slope = calibration_intercept_slope(p, y)

    def intercept_of(q: FloatArray, t: IntArray) -> float:
        return calibration_intercept_slope(q, t)[0]

    def slope_of(q: FloatArray, t: IntArray) -> float:
        return calibration_intercept_slope(q, t)[1]

    def bss_of(q: FloatArray, t: IntArray) -> float:
        return brier_skill_score(q, t, training_rate)

    statistics: dict[str, Statistic] = {
        "brier": brier_score,
        "brier_skill_score": bss_of,
        "log_loss": log_loss,
        "calibration_intercept": intercept_of,
        "calibration_slope": slope_of,
        "roc_auc": roc_auc,
        "average_precision": average_precision,
    }
    participants_with_positive = len({g for g, t in zip(group_array, y, strict=True) if t == 1})

    return {
        "counts": {
            "participants": int(np.unique(group_array).size),
            "participants_with_any_positive": participants_with_positive,
            "meals": int(y.size),
            "positives": int(y.sum()),
            "negatives": int(y.size - y.sum()),
            "observed_rate": float(y.mean()),
        },
        "calibration": {
            "brier": brier_score(p, y),
            "brier_skill_score_vs_training_rate": bss_of(p, y),
            "log_loss": log_loss(p, y),
            "log_loss_clip_eps": EPS,
            "log_loss_predictions_clipped": clipped,
            "calibration_intercept": intercept,
            "calibration_slope": slope,
            "mean_predicted": float(p.mean()),
            "observed_rate": float(y.mean()),
        },
        "discrimination": {
            "roc_auc": roc_auc(p, y),
            "average_precision": average_precision(p, y),
            "note": "Discrimination (ranking) only; these do not measure calibration.",
        },
        "constant_training_rate_baseline": {
            "rate": training_rate,
            "brier": brier_score(constant, y),
            "log_loss": log_loss(constant, y),
            "average_precision": float(y.mean()),
            "note": "Predicts the training positive rate for every meal; ROC-AUC is 0.5.",
        },
        "reliability_equal_size_bins": reliability_table(p, y),
        "participant_cluster_bootstrap": {
            name: cluster_bootstrap(p, y, group_array, fn, resamples, seed)
            for name, fn in statistics.items()
        },
        "leave_one_participant_out": {
            name: leave_one_participant_out(p, y, group_array, fn)
            for name, fn in statistics.items()
        },
    }


def exploratory_criteria(results: Mapping[str, Any]) -> dict[str, Any]:
    """Phase A exploratory checks. Meeting them does not establish reliable calibration."""
    boot = results["participant_cluster_bootstrap"]
    bss_low = boot["brier_skill_score"]["percentile95"][0]
    intercept_ci = boot["calibration_intercept"]["percentile95"]
    slope = results["calibration"]["calibration_slope"]
    low, high = EXPLORATORY_SLOPE_RANGE

    def met(condition: bool, *values: float) -> bool | None:
        return None if any(not math.isfinite(v) for v in values) else condition

    return {
        "status": "exploratory; not clinical or universal standards",
        "brier_skill_lower95_above_0": met(bss_low > 0, bss_low),
        "calibration_intercept_ci95_includes_0": met(
            intercept_ci[0] <= 0 <= intercept_ci[1], *intercept_ci
        ),
        "calibration_slope_point_in_0.7_to_1.3": met(low <= slope <= high, slope),
        "caveat": (
            "With seven participant clusters, intervals are wide and unstable. An interval that "
            "includes a reference value, or a point estimate inside a chosen range, does not by "
            "itself show that the model is reliably calibrated."
        ),
    }


# --- privacy and artefact safety ----------------------------------------------------------


def assert_aggregate_only(report: Any, forbidden: set[str], max_list_length: int = 10) -> None:
    """Fail if the report contains a forbidden token (ID or timestamp) or a long list.

    Tokens match only when not surrounded by letters or digits, so an ID such as "012" inside
    a SHA-256 hash is not a false alarm.
    """
    patterns = [
        re.compile(rf"(?<![0-9A-Za-z]){re.escape(token)}(?![0-9A-Za-z])")
        for token in forbidden
        if token
    ]

    def check_text(text: str, path: str) -> None:
        if any(pattern.search(text) for pattern in patterns):
            raise ValueError(f"Report text at {path} contains a forbidden value.")

    def walk(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                check_text(str(key), path)
                walk(item, f"{path}.{key}")
        elif isinstance(value, list | tuple):
            if len(value) > max_list_length:
                raise ValueError(f"Report list at {path} looks row-level ({len(value)} items).")
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")
        elif isinstance(value, str):
            check_text(value, path)

    walk(report, "report")


def hash_files(paths: Sequence[Path]) -> dict[str, str]:
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def _finite_or_none(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _finite_or_none(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_finite_or_none(v) for v in value]
    return value


# --- deployed-model scoring ---------------------------------------------------------------


@dataclass(frozen=True)
class ValidationScores:
    scores: FloatArray
    labels: IntArray
    groups: list[str]
    forbidden_tokens: set[str]
    verification: dict[str, Any]
    training_rate: float
    model_version: str
    decision_threshold: float


def score_validation_with_deployed_model(model_dir: Path) -> ValidationScores:
    """Score validation meals with the deployed artefact and verify against stored outputs."""
    import os

    import pandas as pd

    from c2_glycemic_forecasting import dietary_risk
    from c2_glycemic_forecasting.trajectory_features import FEATURE_NAMES

    # Load through the service loader (integrity checks), then restore the environment.
    previous = os.environ.get("C2_DIETARY_RISK_MODEL_DIR")
    os.environ["C2_DIETARY_RISK_MODEL_DIR"] = str(model_dir)
    try:
        dietary_risk.load_classifier.cache_clear()
        classifier = dietary_risk.load_classifier()
    finally:
        dietary_risk.load_classifier.cache_clear()
        if previous is None:
            os.environ.pop("C2_DIETARY_RISK_MODEL_DIR", None)
        else:
            os.environ["C2_DIETARY_RISK_MODEL_DIR"] = previous
    metadata = json.loads((model_dir / METADATA_FILE).read_text(encoding="utf-8"))

    trainer = _load_training_script()
    meals = trainer.load_meals(Path(metadata["clean_file"]), Path(metadata["label_file"]))
    if "test" in set(meals["split"]):
        raise RuntimeError("Test participants must never be loaded.")
    meals = meals.loc[(meals["split"] == "validation") & meals["primary_eligible"]]
    meals = trainer.add_features(meals.reset_index(drop=True))

    features = meals[list(FEATURE_NAMES)].to_numpy(dtype=np.float64)
    matrix = xgb.DMatrix(features, feature_names=list(FEATURE_NAMES), missing=np.nan)
    scores = np.asarray(classifier.booster.predict(matrix), dtype=np.float64)

    # The deployed Boolean method must agree with score >= threshold for every meal.
    boolean_matches = sum(
        classifier.estimate_above_threshold(dict(zip(FEATURE_NAMES, row, strict=True)))
        == bool(score >= classifier.threshold)
        for row, score in zip(features, scores, strict=True)
    )

    stored = pd.read_csv(model_dir / STORED_PREDICTIONS, dtype={"participant_id": str})
    joined = (
        meals[["participant_id", "meal_timestamp"]]
        .assign(score=scores)
        .merge(
            stored[["participant_id", "meal_timestamp", "score_all_features"]],
            on=["participant_id", "meal_timestamp"],
            how="inner",
            validate="one_to_one",
        )
    )
    max_difference = float(np.abs(joined["score"] - joined["score_all_features"]).max())

    counts = metadata["counts"]
    verification = {
        "model_version": classifier.model_version,
        "model_sha256_verified_by_loader": metadata["model_sha256"],
        "decision_threshold": classifier.threshold,
        "meals_scored": int(scores.size),
        "meals_matched_to_stored_predictions": int(len(joined)),
        "max_abs_difference_from_stored_scores": max_difference,
        "boolean_indicator_matches_score_threshold": f"{boolean_matches}/{scores.size}",
    }
    if len(joined) != scores.size or max_difference > SCORE_MATCH_TOLERANCE:
        raise RuntimeError("Recomputed scores do not match the deployed model's stored scores.")
    if boolean_matches != scores.size:
        raise RuntimeError("The Boolean indicator disagrees with score >= threshold.")

    groups = meals["participant_id"].astype(str).tolist()
    forbidden = set(groups) | set(meals["meal_timestamp"].astype(str))
    return ValidationScores(
        scores=scores,
        labels=meals[trainer.LABEL].to_numpy(dtype=np.int64),
        groups=groups,
        forbidden_tokens=forbidden,
        verification=verification,
        training_rate=counts["train_primary_positive"] / counts["train_primary_meals"],
        model_version=classifier.model_version,
        decision_threshold=classifier.threshold,
    )


def run(
    model_dir: Path,
    output_dir: Path,
    gru_checkpoint: Path,
    overwrite: bool = False,
    scorer: Callable[[Path], ValidationScores] = score_validation_with_deployed_model,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> dict[str, Any]:
    """Score, evaluate, check privacy and artefact integrity, then write the report."""
    report_path = output_dir / REPORT_FILE
    if report_path.exists() and not overwrite:
        raise FileExistsError(f"{report_path} already exists.")
    if output_dir.resolve() == model_dir.resolve():
        raise ValueError("The output directory must be separate from the model artefacts.")

    protected = [p for p in model_dir.iterdir() if p.is_file()] + [gru_checkpoint]
    before = hash_files(protected)

    data = scorer(model_dir)
    results = evaluate(data.scores, data.labels, data.groups, data.training_rate, resamples)
    report: dict[str, Any] = {
        "description": (
            "Calibration evaluation of the deployed C2 XGBoost post-meal response model on "
            "validation participants. No calibrator was fitted; nothing was trained or tuned."
        ),
        "target_event": (
            "At least one genuine Libre reading above 180 mg/dL from +15 to +240 minutes after "
            "the meal (research-defined; not a diagnosis or a clinically validated risk score)."
        ),
        "model_version": data.model_version,
        "decision_threshold_unchanged": data.decision_threshold,
        "verification": data.verification,
        "training_positive_rate": data.training_rate,
        "seed": SEED,
        "bootstrap_resamples": resamples,
        "results": results,
        "exploratory_criteria": exploratory_criteria(results),
        "limitations": [
            "Seven validation participants (four with any positive meal): participant-level "
            "intervals are wide, and a percentile bootstrap over so few clusters can understate "
            "uncertainty.",
            "The GRU checkpoint was selected on validation loss and the classifier uses "
            "GRU-derived features, so validation is not fully untouched; only the sealed test "
            "set is.",
            "CGMacros data, not a Sri Lankan clinical validation cohort.",
            "Population-level calibration says nothing about calibration for an individual.",
            "Meals preceded by another meal within four hours are excluded, as in training.",
        ],
    }

    after = hash_files(protected)
    if after != before:
        raise RuntimeError("A protected model artefact changed during evaluation.")
    report["protected_artefact_sha256_unchanged"] = before

    report = _finite_or_none(report)
    assert_aggregate_only(report, data.forbidden_tokens)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    from c2_glycemic_forecasting import model as gru_model

    report = run(args.model_dir, args.output_dir, gru_model._checkpoint_path(), args.overwrite)
    results = report["results"]
    LOGGER.info("Counts: %s", results["counts"])
    LOGGER.info("Calibration: %s", results["calibration"])
    LOGGER.info("Discrimination: %s", results["discrimination"])
    LOGGER.info("Report written to %s", args.output_dir / REPORT_FILE)


if __name__ == "__main__":
    main()
