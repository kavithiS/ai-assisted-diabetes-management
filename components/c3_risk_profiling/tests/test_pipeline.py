"""Automated tests. Run from the project root:  pytest -v

These prove the functions behave correctly, which is PP1 testing evidence.
Screenshot the passing output and save it in outputs/reports/.
"""
import pytest
from src.predict import predict_risk, categorise, to_frame, load_model, EXAMPLE_PATIENT


def test_prediction_returns_valid_probability():
    out = predict_risk(EXAMPLE_PATIENT)
    assert 0.0 <= out["risk_probability"] <= 1.0
    assert out["risk_category"] in {"Low", "Moderate", "High"}


def test_risk_bands_are_ordered():
    assert categorise(0.10) == "Low"
    assert categorise(0.50) == "Moderate"
    assert categorise(0.90) == "High"


def test_missing_fields_are_reported_not_hidden():
    partial = {"BMI": 31.0, "HighBP": 1}
    out = predict_risk(partial)
    assert out["data_complete"] is False
    assert len(out["missing_fields"]) > 0


def test_feature_order_matches_training():
    _, features = load_model()
    X, _ = to_frame(EXAMPLE_PATIENT, features)
    assert list(X.columns) == features


def test_higher_risk_profile_scores_higher():
    """Directional sanity check: a worse profile should not score lower."""
    low = dict(EXAMPLE_PATIENT, HighBP=0, HighChol=0, BMI=22.0,
               GenHlth=1, PhysActivity=1, Age=3)
    high = dict(EXAMPLE_PATIENT, HighBP=1, HighChol=1, BMI=38.0,
                GenHlth=5, PhysActivity=0, Age=12)
    assert predict_risk(high)["risk_probability"] > predict_risk(low)["risk_probability"]


def test_extreme_values_do_not_crash():
    for bmi in (12.0, 60.0):
        assert predict_risk(dict(EXAMPLE_PATIENT, BMI=bmi))["risk_probability"] >= 0


@pytest.mark.slow
def test_explanations_return_requested_number_of_factors():
    from src.explain import shap_explain, lime_explain
    assert len(shap_explain(EXAMPLE_PATIENT)) == 5
    assert len(lime_explain(EXAMPLE_PATIENT)) == 5
