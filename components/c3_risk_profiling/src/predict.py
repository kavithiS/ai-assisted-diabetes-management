"""FUNCTION 1 - Multi-factor diabetes risk prediction.

INPUT      a patient record (dict of risk factors)
PROCESSING validation -> feature alignment -> trained model
OUTPUT     risk probability + risk category + data-completeness status

Run the built-in example:
    python -m src.predict
"""

import joblib
import pandas as pd

from .config import CFG, abs_path


def load_model(name: str | None = None):
    name = name or CFG["model"]["active"]
    path = abs_path(CFG["model"]["output_dir"]) / f"{name}.joblib"
    if not path.exists():
        raise FileNotFoundError(f"No trained model at {path}. Run: python -m src.train")
    bundle = joblib.load(path)
    return bundle["model"], bundle["features"]


def to_frame(patient: dict, features: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Put the patient's values in the exact column order the model was trained on.

    Any field the caller omits is filled with 0 and reported back, so the user is
    told the result is based on incomplete data rather than being misled.
    """
    missing = [f for f in features if f not in patient]
    row = {f: patient.get(f, 0) for f in features}
    return pd.DataFrame([row])[features], missing


def categorise(probability: float) -> str:
    bands = CFG["risk_bands"]
    if probability <= bands["low_max"]:
        return "Low"
    if probability <= bands["moderate_max"]:
        return "Moderate"
    return "High"


def predict_risk(patient: dict, model_name: str | None = None) -> dict:
    model, features = load_model(model_name)
    X, missing = to_frame(patient, features)
    probability = float(model.predict_proba(X)[0, 1])
    return {
        "risk_probability": round(probability, 4),
        "risk_percent": round(probability * 100, 1),
        "risk_category": categorise(probability),
        "model_used": model_name or CFG["model"]["active"],
        "missing_fields": missing,
        "data_complete": len(missing) == 0,
        "disclaimer": (
            "Statistical risk estimate for self-management support. "
            "This is not a diagnosis and does not replace medical advice."
        ),
    }


# A sample patient for testing. Field names must match the dataset columns.
EXAMPLE_PATIENT = {
    "HighBP": 1,
    "HighChol": 1,
    "CholCheck": 1,
    "BMI": 29.4,
    "Smoker": 0,
    "Stroke": 0,
    "HeartDiseaseorAttack": 0,
    "PhysActivity": 0,
    "Fruits": 0,
    "Veggies": 1,
    "HvyAlcoholConsump": 0,
    "AnyHealthcare": 1,
    "NoDocbcCost": 0,
    "GenHlth": 3,
    "MentHlth": 2,
    "PhysHlth": 5,
    "DiffWalk": 0,
    "Sex": 1,
    "Age": 9,
    "Education": 5,
    "Income": 6,
}

if __name__ == "__main__":
    import json

    print(json.dumps(predict_risk(EXAMPLE_PATIENT), indent=2))
