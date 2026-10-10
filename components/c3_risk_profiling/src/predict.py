"""FUNCTION 1 - Multi-factor diabetes risk prediction.

INPUT      a patient record (dict of risk factors)
PROCESSING validation -> completeness check -> model choice (with / without
           glucose) -> trained classifier -> calibration -> risk band
OUTPUT     calibrated risk probability + Low / Moderate / High band
           + data-completeness status + referral note

Run the built-in examples:
    python -m src.predict
"""

from functools import cache

import joblib
import numpy as np
import pandas as pd

from .config import CFG, abs_path
from .train import apply_calibrator, categorise

MODEL_DIR = abs_path(CFG["model"]["output_dir"])

# Plausible input ranges. Values outside them are rejected, not guessed.
VALID_RANGES = {
    "age": (18, 100),
    "bmi": (12, 70),
    "systolic_bp": (70, 260),
    "diastolic_bp": (40, 150),
    "pulse_rate": (35, 200),
    "glucose_mmol": (1.5, 40),
}
BINARY = [
    "sex_male",
    "family_history_diabetes",
    "family_history_hypertension",
    "hypertensive",
    "cardiovascular_disease",
    "stroke",
]

DISCLAIMER = (
    "Statistical risk estimate for self-management support. "
    "This is not a diagnosis and does not replace medical advice."
)
REFERRAL = (
    "Because the estimate is in the High band, please arrange a blood test "
    "and a check-up with a doctor or a diabetes clinic."
)


@cache
def load_bundle(feature_set: str) -> dict:
    path = MODEL_DIR / f"c3_{feature_set}.joblib"
    if not path.exists():
        raise FileNotFoundError(f"No trained model at {path}. Run: python -m src.train")
    return joblib.load(path)


def has_value(patient: dict, field: str) -> bool:
    value = patient.get(field)
    return value is not None and not (isinstance(value, float) and np.isnan(value))


def validate(patient: dict) -> list[str]:
    """Return a list of problems. An empty list means the input is usable."""
    problems = []
    for field, (low, high) in VALID_RANGES.items():
        if has_value(patient, field) and not low <= float(patient[field]) <= high:
            problems.append(f"{field}={patient[field]} is outside {low}-{high}")
    for field in BINARY:
        if has_value(patient, field) and patient[field] not in (0, 1):
            problems.append(f"{field} must be 0 or 1")
    return problems


def choose_feature_set(patient: dict) -> str:
    """Use the glucose model only when a glucose result was actually given."""
    return "with_glucose" if has_value(patient, "glucose_mmol") else "without_glucose"


def to_frame(patient: dict, features: list[str], fill_values: dict):
    """Put the values in the exact column order the model was trained on.

    Non-critical gaps are filled with the TRAINING median and reported back,
    so the user is told the result rests on partial data.
    """
    imputed = [f for f in features if not has_value(patient, f)]
    row = {f: float(patient[f]) if has_value(patient, f) else fill_values[f] for f in features}
    return pd.DataFrame([row])[features], imputed


def predict_risk(patient: dict) -> dict:
    base = {"disclaimer": DISCLAIMER}
    problems = validate(patient)
    if problems:
        return {**base, "status": "invalid_input", "problems": problems}

    missing_critical = [f for f in CFG["critical_fields"] if not has_value(patient, f)]
    if missing_critical:
        # FR12: no unsupported category is returned when critical data is missing.
        return {**base, "status": "insufficient_data", "missing_critical_fields": missing_critical}

    feature_set = choose_feature_set(patient)
    bundle = load_bundle(feature_set)
    X, imputed = to_frame(patient, bundle["features"], bundle["fill_values"])
    raw = float(bundle["model"].predict_proba(X)[0, 1])
    probability = float(apply_calibrator(bundle["calibrator"], [raw])[0])
    category = categorise(probability, bundle["thresholds"])
    return {
        **base,
        "status": "ok",
        "risk_probability": round(probability, 4),
        "risk_percent": round(probability * 100, 1),
        "risk_category": category,
        "model_used": bundle["model_name"],
        "feature_set": feature_set,
        "model_version": bundle["version"],
        "thresholds": bundle["thresholds"],
        "imputed_fields": imputed,
        "data_complete": not imputed,
        "referral": REFERRAL if category == "High" else None,
    }


# Two demo patients. Field names match config.yaml feature_sets.
EXAMPLE_PATIENT = {
    "age": 58,
    "sex_male": 1,
    "bmi": 27.8,
    "systolic_bp": 150,
    "diastolic_bp": 95,
    "pulse_rate": 84,
    "glucose_mmol": 9.8,
    "family_history_diabetes": 1,
    "family_history_hypertension": 1,
    "hypertensive": 1,
    "cardiovascular_disease": 0,
    "stroke": 0,
}
LOW_RISK_PATIENT = {
    "age": 29,
    "sex_male": 0,
    "bmi": 21.5,
    "systolic_bp": 112,
    "diastolic_bp": 72,
    "pulse_rate": 72,
    "glucose_mmol": 5.4,
    "family_history_diabetes": 0,
    "family_history_hypertension": 0,
    "hypertensive": 0,
    "cardiovascular_disease": 0,
    "stroke": 0,
}

if __name__ == "__main__":
    import json

    for label, patient in [
        ("Higher-risk example", EXAMPLE_PATIENT),
        ("Lower-risk", LOW_RISK_PATIENT),
    ]:
        print(f"\n{label}:")
        print(json.dumps(predict_risk(patient), indent=2))
    no_glucose = {k: v for k, v in EXAMPLE_PATIENT.items() if k != "glucose_mmol"}
    print("\nSame higher-risk patient without a glucose result:")
    print(json.dumps(predict_risk(no_glucose), indent=2))
    print("\nMissing blood pressure (critical):")
    print(json.dumps(predict_risk({"age": 50, "bmi": 30}), indent=2))
