"""Tests for the dietary-risk training script. Synthetic data and a stub GRU only."""

import importlib.util
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd
import pytest

from c2_glycemic_forecasting.trajectory_features import FEATURE_NAMES

TRAINING_DIR = Path(__file__).resolve().parents[1] / "training"


def _load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"c2_training_{name}", TRAINING_DIR / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


trainer = _load_script("train_dietary_risk_xgb")


# --- metrics ------------------------------------------------------------------------------


def test_classification_metrics_counts() -> None:
    labels = np.array([1, 1, 1, 0, 0, 0, 0])
    predicted = np.array([1, 1, 0, 1, 0, 0, 0])

    metrics = trainer.classification_metrics(labels, predicted)

    assert (metrics["tp"], metrics["fp"], metrics["fn"], metrics["tn"]) == (2, 1, 1, 3)
    assert metrics["precision"] == pytest.approx(2 / 3)
    assert metrics["recall"] == pytest.approx(2 / 3)
    assert metrics["specificity"] == pytest.approx(3 / 4)
    assert metrics["f1"] == pytest.approx(2 / 3)


def test_metrics_are_nan_when_undefined() -> None:
    metrics = trainer.classification_metrics(np.array([0, 0]), np.array([0, 0]))

    assert np.isnan(metrics["precision"])
    assert np.isnan(metrics["recall"])
    assert np.isnan(trainer.roc_auc(np.array([0, 0]), np.array([0.1, 0.2])))


def test_roc_auc_known_values() -> None:
    labels = np.array([0, 0, 1, 1])
    assert trainer.roc_auc(labels, np.array([0.1, 0.2, 0.8, 0.9])) == 1.0
    assert trainer.roc_auc(labels, np.array([0.9, 0.8, 0.2, 0.1])) == 0.0
    assert trainer.roc_auc(labels, np.array([0.5, 0.5, 0.5, 0.5])) == 0.5
    # One of four positive-negative pairs is ranked wrongly.
    assert trainer.roc_auc(labels, np.array([0.1, 0.6, 0.5, 0.9])) == 0.75


def test_average_precision_known_values() -> None:
    labels = np.array([1, 0, 1, 0])
    # Ranked: 1 (P=1), 0, 1 (P=2/3), 0 -> (1 + 2/3) / 2.
    assert trainer.average_precision(labels, np.array([0.9, 0.8, 0.7, 0.1])) == pytest.approx(5 / 6)
    assert trainer.average_precision(np.array([1, 1, 0]), np.array([0.9, 0.8, 0.1])) == 1.0
    # A single tie group: precision is the positive rate.
    assert trainer.average_precision(labels, np.full(4, 0.5)) == pytest.approx(0.5)


def test_best_f1_threshold() -> None:
    labels = np.array([0, 0, 1, 1])
    assert trainer.best_f1_threshold(labels, np.array([0.1, 0.2, 0.7, 0.8])) == pytest.approx(0.7)


# --- folds --------------------------------------------------------------------------------


def test_participant_folds_are_disjoint_complete_and_deterministic() -> None:
    participants = [f"{i:03d}" for i in range(31)] * 3

    folds = trainer.participant_folds(participants, 5, seed=42)

    flattened = [p for fold in folds for p in fold]
    assert sorted(flattened) == sorted(set(participants))
    assert len(flattened) == len(set(flattened))
    assert sorted(len(fold) for fold in folds) == [6, 6, 6, 6, 7]
    assert folds == trainer.participant_folds(list(reversed(participants)), 5, seed=42)


def test_participant_folds_need_enough_participants() -> None:
    with pytest.raises(ValueError):
        trainer.participant_folds(["001", "002"], 5, seed=42)


def test_out_of_fold_scores_never_train_on_held_out_participants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    participants = pd.Series(["a", "a", "b", "b", "c", "c"])
    features = pd.DataFrame({"x": np.arange(6.0)})
    labels = np.array([0, 1, 0, 1, 0, 1])
    seen: list[set[float]] = []

    def fake_fit(x: pd.DataFrame, y: np.ndarray, config: dict[str, object]) -> set[float]:
        seen.append(set(x["x"]))
        return set(x["x"])

    monkeypatch.setattr(trainer, "fit_booster", fake_fit)
    monkeypatch.setattr(trainer, "predict_booster", lambda b, x: np.zeros(len(x)))

    trainer.out_of_fold_scores(features, labels, participants, [["a"], ["b"], ["c"]], {})

    assert seen == [{2.0, 3.0, 4.0, 5.0}, {0.0, 1.0, 4.0, 5.0}, {0.0, 1.0, 2.0, 3.0}]


# --- end to end on synthetic data ---------------------------------------------------------


def stub_gru(features: Sequence[float]) -> list[float]:
    """Deterministic stand-in for the GRU: rises with carbohydrate, peaks at +60 minutes."""
    premeal, _, carbs = features[0], features[1], features[2]
    peak = premeal + 1.2 * carbs
    return [
        premeal + (peak - premeal) * min(m, 60) / 60 * (1 - max(m - 60, 0) / 300)
        for m in range(15, 241, 15)
    ]


def write_synthetic(tmp_path: Path) -> tuple[Path, Path]:
    rng = np.random.default_rng(0)
    clean_rows, label_rows = [], []
    for index in range(12):
        participant = f"{index:03d}"
        split = "validation" if index >= 9 else "train"
        for meal in range(15):
            premeal = float(rng.uniform(80, 160))
            carbs = float(rng.uniform(0, 120))
            stamp = f"2030-01-{meal + 1:02d}T08:00:00"
            clean_rows.append(
                {
                    "participant_id": participant,
                    "split": split,
                    "meal_timestamp": stamp,
                    "premeal_libre_gl": premeal,
                    "calories": carbs * 4 + 200,
                    "carbs": carbs,
                    "protein": 20.0,
                    "fat": 10.0,
                    "fiber": 5.0,
                    # Observed outcomes: must never reach the features.
                    **{f"libre_gl_t{m:03d}": premeal + carbs for m in range(0, 241, 15)},
                }
            )
            label = int(premeal + 1.2 * carbs + rng.normal(0, 15) > 180)
            label_rows.append(
                {
                    "participant_id": participant,
                    "split": split,
                    "meal_timestamp": stamp,
                    "above_180_within_4h": label,
                    "label_valid": True,
                    "isolated_meal": meal % 5 != 0,
                    "primary_eligible": meal % 5 != 0,
                    "observed_max_glucose": 200.0 if label else 150.0,
                }
            )
    clean_file, label_file = tmp_path / "clean.csv", tmp_path / "labels.csv"
    pd.DataFrame(clean_rows).to_csv(clean_file, index=False)
    pd.DataFrame(label_rows).to_csv(label_file, index=False)
    return clean_file, label_file


@pytest.fixture
def stubbed_gru(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    checkpoint = tmp_path / "gru.pt"
    checkpoint.write_bytes(b"stub")
    monkeypatch.setattr(trainer.gru_model, "predict_glucose", stub_gru)
    monkeypatch.setattr(trainer.gru_model, "_checkpoint_path", lambda: checkpoint)
    monkeypatch.setattr(
        trainer, "GRID", {"max_depth": (2,), "num_boost_round": (20, 40), "min_child_weight": (1,)}
    )


@pytest.mark.usefixtures("stubbed_gru")
def test_run_writes_model_metadata_and_metrics(tmp_path: Path) -> None:
    clean_file, label_file = write_synthetic(tmp_path)
    output = tmp_path / "out"

    metrics = trainer.run(clean_file, label_file, output)

    metadata = json.loads((output / trainer.METADATA_FILE).read_text(encoding="utf-8"))
    assert metadata["feature_names"] == list(FEATURE_NAMES)
    assert 0 < metadata["decision_threshold"] < 1
    assert metadata["model_version"].startswith("xgb-above180-4h-")
    assert metadata["counts"]["train_participants"] == 9
    assert metadata["counts"]["validation_participants"] == 3
    # Validation and training participants are disjoint, and folds cover only training ones.
    fold_participants = {p for fold in metadata["folds"] for p in fold}
    assert fold_participants == {f"{i:03d}" for i in range(9)}
    assert set(metrics["validation"]) == {
        "xgboost_all_features",
        "xgboost_nutrition_only",
        "gru_peak_rule",
        "no_skill_positive_rate",
    }
    assert metrics["counts"]["validation_preceded_meals"] == 9
    predictions = pd.read_csv(output / "validation_predictions.csv", dtype={"participant_id": str})
    assert set(predictions["participant_id"]) == {"009", "010", "011"}

    with pytest.raises(FileExistsError):
        trainer.run(clean_file, label_file, output)


@pytest.mark.usefixtures("stubbed_gru")
def test_features_do_not_depend_on_observed_post_meal_glucose(tmp_path: Path) -> None:
    clean_file, label_file = write_synthetic(tmp_path)
    meals = trainer.load_meals(clean_file, label_file)
    changed = meals.copy()
    outcome_columns = [c for c in meals.columns if c.startswith("libre_gl_t")]
    changed[outcome_columns] = 400.0

    original = trainer.add_features(meals)[list(FEATURE_NAMES)]
    after = trainer.add_features(changed)[list(FEATURE_NAMES)]

    pd.testing.assert_frame_equal(original, after)
    assert not any("libre" in name for name in FEATURE_NAMES)


def test_load_meals_rejects_missing_labels(tmp_path: Path) -> None:
    clean_file, label_file = write_synthetic(tmp_path)
    labels = pd.read_csv(label_file, dtype={"participant_id": str})
    labels.iloc[1:].to_csv(label_file, index=False)

    with pytest.raises(ValueError, match="exactly one label"):
        trainer.load_meals(clean_file, label_file)


def test_load_meals_drops_test_split(tmp_path: Path) -> None:
    clean_file, label_file = write_synthetic(tmp_path)
    clean = pd.read_csv(clean_file, dtype={"participant_id": str})
    clean.loc[clean["participant_id"] == "011", "split"] = "test"
    clean.to_csv(clean_file, index=False)

    meals = trainer.load_meals(clean_file, label_file)

    assert "011" not in set(meals["participant_id"])
