"""Automated tests. Run from the project root:  python -m pytest -v

These prove the functions behave correctly, which is PP1 testing evidence.
They use generated stand-in models (tests/conftest.py), so they run without the
dataset. Screenshot the passing output and save it in outputs/reports/.
"""

import numpy as np
import pandas as pd
import pytest
from src.predict import (
    EXAMPLE_PATIENT,
    LOW_RISK_PATIENT,
    load_bundle,
    predict_risk,
    to_frame,
)
from src.south_asia_dataset import apply_plausibility
from src.synthetic import GaussianCopulaSynthesizer, exact_copy_rate
from src.train import apply_calibrator, categorise, choose_thresholds, fit_calibrator
from tests.conftest import fake_patients

# ---------- Function 1: risk prediction ----------


def test_prediction_returns_valid_probability_and_band(fake_models):
    out = predict_risk(EXAMPLE_PATIENT)
    assert out["status"] == "ok"
    assert 0.0 <= out["risk_probability"] <= 1.0
    assert out["risk_category"] in {"Low", "Moderate", "High"}
    assert "not a diagnosis" in out["disclaimer"]


def test_glucose_decides_which_model_is_used(fake_models):
    assert predict_risk(EXAMPLE_PATIENT)["feature_set"] == "with_glucose"
    no_glucose = dict(EXAMPLE_PATIENT, glucose_mmol=None)
    assert predict_risk(no_glucose)["feature_set"] == "without_glucose"


def test_missing_critical_field_returns_no_band(fake_models):
    """FR12: no unsupported category when critical data is missing."""
    out = predict_risk({"age": 50, "bmi": 30})
    assert out["status"] == "insufficient_data"
    assert "risk_category" not in out
    assert set(out["missing_critical_fields"]) == {"systolic_bp", "diastolic_bp"}


def test_missing_optional_field_is_reported_not_hidden(fake_models):
    partial = {k: v for k, v in EXAMPLE_PATIENT.items() if k != "pulse_rate"}
    out = predict_risk(partial)
    assert out["status"] == "ok"
    assert out["data_complete"] is False
    assert out["imputed_fields"] == ["pulse_rate"]


def test_impossible_values_are_rejected(fake_models):
    out = predict_risk(dict(EXAMPLE_PATIENT, bmi=500))
    assert out["status"] == "invalid_input"
    assert predict_risk(dict(EXAMPLE_PATIENT, stroke=3))["status"] == "invalid_input"


def test_feature_order_matches_training(fake_models):
    bundle = load_bundle("with_glucose")
    X, _ = to_frame(EXAMPLE_PATIENT, bundle["features"], bundle["fill_values"])
    assert list(X.columns) == bundle["features"]


def test_higher_risk_profile_scores_higher(fake_models):
    """Directional sanity check: a worse profile should not score lower."""
    assert (
        predict_risk(EXAMPLE_PATIENT)["risk_probability"]
        > predict_risk(LOW_RISK_PATIENT)["risk_probability"]
    )


def test_high_band_carries_referral(fake_models):
    out = predict_risk(EXAMPLE_PATIENT)
    assert (out["referral"] is not None) == (out["risk_category"] == "High")


def test_extreme_but_valid_values_do_not_crash(fake_models):
    for bmi in (12.0, 70.0):
        assert predict_risk(dict(EXAMPLE_PATIENT, bmi=bmi))["status"] == "ok"


# ---------- Calibration and risk bands ----------


def test_risk_bands_are_ordered():
    t = {"low_max": 0.05, "high_min": 0.2}
    assert categorise(0.01, t) == "Low"
    assert categorise(0.10, t) == "Moderate"
    assert categorise(0.50, t) == "High"


def test_thresholds_come_from_data_and_are_ordered():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 500)
    scores = np.clip(0.3 * y + rng.normal(0.3, 0.15, 500), 0.01, 0.99)
    t = choose_thresholds(scores, y)
    assert 0 < t["low_max"] <= t["high_min"] < 1


def test_calibration_keeps_ranking():
    scores = np.linspace(0.05, 0.95, 50)
    y = (scores + np.random.default_rng(2).normal(0, 0.2, 50) > 0.5).astype(int)
    calibrated = apply_calibrator(fit_calibrator(scores, y), scores)
    assert np.all(np.diff(calibrated) >= 0)


# ---------- Data quality and synthetic data ----------


def test_impossible_values_become_missing():
    df = pd.DataFrame(
        {
            "bmi": [574.0, 22.0],
            "systolic_bp": [120, 30],
            "diastolic_bp": [80, 80],
            "pulse_rate": [5, 70],
            "glucose_mmol": [6.0, 0.0],
        }
    )
    out = apply_plausibility(df)
    assert out.isna().sum().to_dict() == {
        "bmi": 1,
        "systolic_bp": 1,
        "diastolic_bp": 0,
        "pulse_rate": 1,
        "glucose_mmol": 1,
    }


def test_synthetic_rows_keep_shape_labels_and_binary_columns():
    X, y = fake_patients(400, seed=3)
    X_syn, y_syn = GaussianCopulaSynthesizer(5).fit(X, y).sample(400)
    assert list(X_syn.columns) == list(X.columns)
    assert not X_syn.isna().any().any()
    assert set(y_syn.unique()) <= {0, 1}
    assert abs(y_syn.mean() - y.mean()) < 0.02
    assert set(X_syn["hypertensive"].unique()) <= {0, 1}
    assert X_syn["age"].between(X["age"].min(), X["age"].max()).all()
    assert exact_copy_rate(X, X_syn) < 0.05


# ---------- Function 2: explanations ----------


@pytest.mark.slow
@pytest.mark.parametrize("glucose", [9.8, None])
def test_explanations_for_both_models(fake_models, glucose):
    from src.explain import explain_patient

    result = explain_patient(dict(EXAMPLE_PATIENT, glucose_mmol=glucose))
    assert len(result["shap"]) == 5
    assert 1 <= len(result["lime"]) <= 5
    assert 0.0 <= result["agreement"]["overlap_ratio"] <= 1.0
    assert all(r["factor_type"] for r in result["shap"])
    assert "not medical causes" in result["explanation_text"]


def test_insufficient_data_skips_explanations(fake_models):
    from src.explain import explain_patient

    result = explain_patient({"age": 50})
    assert set(result) == {"prediction"}
