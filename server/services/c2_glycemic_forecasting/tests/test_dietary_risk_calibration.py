"""Tests for the calibration evaluation. Synthetic data only, except one test against the
deployed artefacts that is skipped when they are not present (for example in CI)."""

import importlib.util
import json
import math
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pytest

TRAINING_DIR = Path(__file__).resolve().parents[1] / "training"


def _load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"c2_training_{name}", TRAINING_DIR / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look up their module by name
    spec.loader.exec_module(module)
    return module


cal = _load_script("evaluate_dietary_risk_calibration")


def bernoulli_sample(n: int, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Predictions and outcomes drawn from those exact probabilities (perfectly calibrated)."""
    rng = np.random.default_rng(seed)
    p = rng.uniform(0.02, 0.98, n)
    y = (rng.uniform(size=n) < p).astype(int)
    return p, y


def logit(p: np.ndarray) -> np.ndarray:
    return np.asarray(np.log(p / (1 - p)), dtype=np.float64)


def expit(z: np.ndarray) -> np.ndarray:
    return np.asarray(1 / (1 + np.exp(-z)), dtype=np.float64)


# --- input checks -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("p", "y", "message"),
    [
        ([0.1, 0.2], [0], "equal length"),
        ([], [], "At least one"),
        ([0.1, math.nan], [0, 1], "finite"),
        ([0.1, 1.2], [0, 1], "within"),
        ([-0.1, 0.5], [0, 1], "within"),
        ([0.1, 0.2], [0, 2], "0 or 1"),
    ],
)
def test_invalid_inputs_are_rejected(p: list[float], y: list[int], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        cal.brier_score(p, y)


# --- Brier, skill, log loss ---------------------------------------------------------------


def test_brier_score_known_value() -> None:
    # (0.1-0)^2 + (0.8-1)^2 + (0.5-1)^2 = 0.01 + 0.04 + 0.25
    assert cal.brier_score([0.1, 0.8, 0.5], [0, 1, 1]) == pytest.approx(0.30 / 3)


def test_brier_skill_score() -> None:
    y = np.array([0, 0, 0, 1])
    assert cal.brier_skill_score(np.full(4, 0.25), y, 0.25) == pytest.approx(0)
    assert cal.brier_skill_score(y.astype(float), y, 0.25) == pytest.approx(1)
    assert cal.brier_skill_score(np.full(4, 0.9), y, 0.25) < 0
    with pytest.raises(ValueError, match="reference"):
        cal.brier_skill_score(np.full(4, 0.5), y, 0.0)


def test_log_loss_known_value_and_clipping() -> None:
    assert cal.log_loss([0.5, 0.5], [0, 1]) == pytest.approx(math.log(2))

    # p = 0 for a positive would be infinite; it is clipped to EPS and counted.
    loss = cal.log_loss([0.0, 1.0], [1, 1])
    assert loss == pytest.approx(-(math.log(cal.EPS) + math.log(1 - cal.EPS)) / 2)
    _, clipped = cal.clip_probabilities([0.0, 0.5, 1.0])
    assert clipped == 2


# --- calibration intercept and slope ------------------------------------------------------


def test_calibrated_predictions_have_intercept_0_and_slope_1() -> None:
    p, y = bernoulli_sample(20000)

    intercept, slope = cal.calibration_intercept_slope(p, y)

    assert intercept == pytest.approx(0, abs=0.06)
    assert slope == pytest.approx(1, abs=0.06)


def test_overconfident_predictions_have_slope_below_1() -> None:
    p, y = bernoulli_sample(20000, seed=1)
    overconfident = expit(2 * logit(p))

    _, slope = cal.calibration_intercept_slope(overconfident, y)

    assert slope == pytest.approx(0.5, abs=0.05)


def test_underpredicting_by_a_constant_gives_positive_intercept() -> None:
    p, y = bernoulli_sample(20000, seed=2)
    shifted = expit(logit(p) - 0.5)

    intercept, slope = cal.calibration_intercept_slope(shifted, y)

    assert intercept == pytest.approx(0.5, abs=0.06)
    assert slope == pytest.approx(1, abs=0.06)


def test_single_class_or_separation_gives_nan_not_a_forced_number() -> None:
    assert all(math.isnan(v) for v in cal.calibration_intercept_slope([0.2, 0.7], [1, 1]))

    # Perfectly separated: the slope diverges.
    p = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])
    y = np.array([0, 0, 0, 1, 1, 1])
    _, slope = cal.calibration_intercept_slope(p, y)
    assert math.isnan(slope)


# --- discrimination -----------------------------------------------------------------------


def test_discrimination_known_values() -> None:
    y = np.array([0, 0, 1, 1])
    assert cal.roc_auc([0.1, 0.6, 0.5, 0.9], y) == 0.75
    assert cal.average_precision([0.9, 0.8, 0.7, 0.1], [1, 0, 1, 0]) == pytest.approx(5 / 6)
    assert math.isnan(cal.roc_auc([0.1, 0.2], [0, 0]))
    assert math.isnan(cal.average_precision([0.1, 0.2], [0, 0]))


# --- reliability table --------------------------------------------------------------------


def test_reliability_table_has_three_equal_size_bins() -> None:
    p, y = bernoulli_sample(116, seed=3)

    table = cal.reliability_table(p, y)

    assert [row["meals"] for row in table] == [39, 39, 38]
    assert sum(row["positives"] for row in table) == y.sum()
    order = np.argsort(p, kind="mergesort")
    first = order[:39]
    assert table[0]["mean_predicted"] == pytest.approx(p[first].mean())
    assert table[0]["observed_rate"] == pytest.approx(y[first].mean())
    assert table[0]["predicted_max"] <= table[1]["predicted_min"]
    low, high = table[0]["observed_rate_wilson95_meal_level"]
    assert 0 <= low <= table[0]["observed_rate"] <= high <= 1


def test_reliability_table_rejects_too_many_bins() -> None:
    with pytest.raises(ValueError, match="bins"):
        cal.reliability_table([0.1, 0.2], [0, 1], bins=3)


def test_wilson_interval() -> None:
    low, high = cal.wilson_interval(0, 10)
    assert low == pytest.approx(0, abs=1e-12)
    assert high == pytest.approx(0.2775, abs=1e-3)
    assert all(math.isnan(v) for v in cal.wilson_interval(0, 0))


# --- participant-level resampling ---------------------------------------------------------


def clustered_sample() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Five participants with 2..6 meals; every prediction value identifies its participant."""
    p, y, groups = [], [], []
    for index, size in enumerate(range(2, 7)):
        for meal in range(size):
            p.append(0.1 * (index + 1) + 0.001 * meal)
            y.append(meal % 2)
            groups.append(f"P{index}")
    return np.array(p), np.array(y), groups


def test_bootstrap_resamples_whole_participants() -> None:
    p, y, groups = clustered_sample()
    sizes = {g: groups.count(g) for g in set(groups)}
    owner = dict(zip(np.round(p, 6), groups, strict=True))

    def check_whole(q: np.ndarray, t: np.ndarray) -> float:
        counts: dict[float, int] = {}
        for value in np.round(q, 6):
            counts[value] = counts.get(value, 0) + 1
        per_group: dict[str, set[int]] = {}
        for value, count in counts.items():
            per_group.setdefault(owner[value], set()).add(count)
        # Every meal of a drawn participant appears the same number of times.
        for group, multiplicities in per_group.items():
            assert len(multiplicities) == 1
            assert sum(1 for v in counts if owner[v] == group) == sizes[group]
        return float(q.size)

    result = cal.cluster_bootstrap(p, y, groups, check_whole, resamples=200, seed=7)

    assert result["clusters"] == 5
    assert result["resamples_used"] + result["skipped_single_class"] == 200


def test_bootstrap_is_deterministic_for_a_seed() -> None:
    p, y, groups = clustered_sample()
    first = cal.cluster_bootstrap(p, y, groups, cal.brier_score, resamples=100, seed=3)
    second = cal.cluster_bootstrap(p, y, groups, cal.brier_score, resamples=100, seed=3)
    assert first == second


def test_bootstrap_skips_single_class_and_non_finite_resamples() -> None:
    # Only participant A has a positive; resamples without A are single-class.
    p = np.array([0.2, 0.8, 0.3, 0.4, 0.5])
    y = np.array([0, 1, 0, 0, 0])
    groups = ["A", "A", "B", "C", "D"]

    result = cal.cluster_bootstrap(p, y, groups, lambda q, t: math.nan, resamples=300, seed=1)

    assert result["skipped_single_class"] > 0
    assert result["resamples_used"] == 0
    assert result["skipped_not_finite"] == 300 - result["skipped_single_class"]
    assert all(math.isnan(v) for v in result["percentile95"])


def test_bootstrap_requires_one_group_per_prediction() -> None:
    with pytest.raises(ValueError, match="Groups"):
        cal.cluster_bootstrap([0.1, 0.9], [0, 1], ["A"], cal.brier_score, resamples=5)


def test_leave_one_participant_out_removes_one_participant_each_time() -> None:
    p, y, groups = clustered_sample()

    result = cal.leave_one_participant_out(p, y, groups, lambda q, t: float(q.size))

    assert result["analyses"] == 5
    assert result["min"] == 20 - 6
    assert result["max"] == 20 - 2
    assert result["not_computable"] == 0


def test_leave_one_participant_out_reports_uncomputable_analyses() -> None:
    p = np.array([0.2, 0.8, 0.3])
    y = np.array([0, 1, 0])
    result = cal.leave_one_participant_out(p, y, ["A", "A", "B"], cal.brier_score)

    assert result["not_computable"] == 1  # removing A leaves a single class


# --- evaluate and exploratory criteria ----------------------------------------------------


def test_evaluate_reports_counts_and_separates_discrimination() -> None:
    p, y, groups = clustered_sample()

    results = cal.evaluate(p, y, groups, training_rate=0.3, resamples=50)

    assert results["counts"] == {
        "participants": 5,
        "participants_with_any_positive": 5,
        "meals": 20,
        "positives": int(y.sum()),
        "negatives": int(20 - y.sum()),
        "observed_rate": pytest.approx(y.mean()),
    }
    assert set(results["discrimination"]) == {"roc_auc", "average_precision", "note"}
    assert "roc_auc" not in results["calibration"]
    baseline = results["constant_training_rate_baseline"]
    assert baseline["brier"] == pytest.approx(np.mean((0.3 - y) ** 2))
    assert len(results["reliability_equal_size_bins"]) == 3
    assert set(results["participant_cluster_bootstrap"]) == set(
        results["leave_one_participant_out"]
    )


def test_exploratory_criteria_are_labelled_and_handle_nan() -> None:
    results: dict[str, Any] = {
        "participant_cluster_bootstrap": {
            "brier_skill_score": {"percentile95": [0.05, 0.3]},
            "calibration_intercept": {"percentile95": [math.nan, math.nan]},
        },
        "calibration": {"calibration_slope": 0.9},
    }

    criteria = cal.exploratory_criteria(results)

    assert "exploratory" in criteria["status"]
    assert criteria["brier_skill_lower95_above_0"] is True
    assert criteria["calibration_intercept_ci95_includes_0"] is None
    assert criteria["calibration_slope_point_in_0.7_to_1.3"] is True


# --- privacy and artefact safety ----------------------------------------------------------


def test_aggregate_check_rejects_identifiers_timestamps_and_row_lists() -> None:
    forbidden = {"012", "2030-01-01T08:00:00"}
    with pytest.raises(ValueError):
        cal.assert_aggregate_only({"note": "participant 012"}, forbidden)
    with pytest.raises(ValueError):
        cal.assert_aggregate_only({"t": ["2030-01-01T08:00:00"]}, forbidden)
    with pytest.raises(ValueError):
        cal.assert_aggregate_only({"012": 1}, forbidden)
    with pytest.raises(ValueError, match="row-level"):
        cal.assert_aggregate_only({"scores": list(range(11))}, forbidden)


def test_aggregate_check_ignores_ids_inside_hashes_and_numbers() -> None:
    cal.assert_aggregate_only(
        {"sha256": "ab012cd9", "meals": 12, "version": "xgb-above180-4h-0012"}, {"012"}
    )


def fake_scorer(model_version: str = "xgb-test", tamper: Path | None = None) -> Any:
    def score(model_dir: Path) -> Any:
        if tamper is not None:
            tamper.write_text("changed", encoding="utf-8")
        p, y, groups = clustered_sample()
        return cal.ValidationScores(
            scores=p,
            labels=y,
            groups=groups,
            forbidden_tokens=set(groups) | {"2030-01-01T08:00:00"},
            verification={"meals_scored": len(p)},
            training_rate=0.3,
            model_version=model_version,
            decision_threshold=0.279,
        )

    return score


@pytest.fixture
def model_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "model"
    directory.mkdir()
    (directory / "dietary_risk_xgb.json").write_text("{}", encoding="utf-8")
    (directory / "metrics.json").write_text("{}", encoding="utf-8")
    return directory


@pytest.fixture
def checkpoint(tmp_path: Path) -> Path:
    path = tmp_path / "gru_best.pt"
    path.write_bytes(b"checkpoint")
    return path


def test_run_writes_aggregate_report_without_touching_artefacts(
    tmp_path: Path, model_dir: Path, checkpoint: Path
) -> None:
    before = {p.name: p.read_bytes() for p in model_dir.iterdir()}
    output = tmp_path / "results_dietary_risk_calibration"

    report = cal.run(model_dir, output, checkpoint, scorer=fake_scorer(), resamples=50)

    saved = json.loads((output / cal.REPORT_FILE).read_text(encoding="utf-8"))
    assert saved["model_version"] == "xgb-test"
    assert saved["decision_threshold_unchanged"] == 0.279
    assert set(saved["protected_artefact_sha256_unchanged"]) == {
        "dietary_risk_xgb.json",
        "metrics.json",
        "gru_best.pt",
    }
    assert {p.name: p.read_bytes() for p in model_dir.iterdir()} == before
    assert report["exploratory_criteria"]["status"].startswith("exploratory")
    text = (output / cal.REPORT_FILE).read_text(encoding="utf-8")
    assert "P0" not in text and "2030-01-01" not in text
    assert "NaN" not in text  # non-finite values are written as null


def test_run_refuses_to_overwrite_or_write_into_model_dir(
    tmp_path: Path, model_dir: Path, checkpoint: Path
) -> None:
    output = tmp_path / "out"
    cal.run(model_dir, output, checkpoint, scorer=fake_scorer(), resamples=10)

    with pytest.raises(FileExistsError):
        cal.run(model_dir, output, checkpoint, scorer=fake_scorer(), resamples=10)
    with pytest.raises(ValueError, match="separate"):
        cal.run(model_dir, model_dir, checkpoint, scorer=fake_scorer(), resamples=10)


def test_run_fails_if_a_protected_artefact_changes(
    tmp_path: Path, model_dir: Path, checkpoint: Path
) -> None:
    scorer = fake_scorer(tamper=model_dir / "metrics.json")

    with pytest.raises(RuntimeError, match="protected"):
        cal.run(model_dir, tmp_path / "out", checkpoint, scorer=scorer, resamples=10)
    assert not (tmp_path / "out" / cal.REPORT_FILE).exists()


def test_run_refuses_a_report_that_would_reveal_an_identifier(
    tmp_path: Path, model_dir: Path, checkpoint: Path
) -> None:
    with pytest.raises(ValueError, match="forbidden"):
        cal.run(
            model_dir,
            tmp_path / "out",
            checkpoint,
            scorer=fake_scorer(model_version="model for P3"),
            resamples=10,
        )
    assert not (tmp_path / "out" / cal.REPORT_FILE).exists()


# --- deployed artefacts -------------------------------------------------------------------


@pytest.mark.skipif(
    not (cal.MODEL_DIR / cal.STORED_PREDICTIONS).is_file(),
    reason="Deployed dietary-risk artefacts are not available.",
)
def test_deployed_model_scores_match_stored_predictions() -> None:
    data = cal.score_validation_with_deployed_model(cal.MODEL_DIR)

    assert data.verification["meals_scored"] == 116
    assert data.verification["meals_matched_to_stored_predictions"] == 116
    assert data.verification["max_abs_difference_from_stored_scores"] <= 1e-6
    assert data.verification["boolean_indicator_matches_score_threshold"] == "116/116"
    assert data.model_version.startswith("xgb-above180-4h-")
    assert len(set(data.groups)) == 7
