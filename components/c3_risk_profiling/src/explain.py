"""FUNCTION 2 - Explainable risk analysis with SHAP and LIME.

INPUT      a patient record + the trained model chosen by Function 1
PROCESSING SHAP (Shapley contributions) and LIME (local surrogate model)
OUTPUT     ranked contributing factors split into modifiable / not modifiable,
           a SHAP-LIME agreement check, LIME fidelity, and a plain-language summary

Run:
    python -m src.explain
"""

import numpy as np
import pandas as pd

from .config import CFG
from .predict import EXAMPLE_PATIENT, choose_feature_set, load_bundle, predict_risk, to_frame

# Plain-language names so the output is readable by a non-technical user.
READABLE = {
    "age": "age",
    "sex_male": "sex",
    "bmi": "body mass index (BMI)",
    "systolic_bp": "systolic blood pressure",
    "diastolic_bp": "diastolic blood pressure",
    "pulse_rate": "resting pulse rate",
    "glucose_mmol": "blood glucose",
    "family_history_diabetes": "family history of diabetes",
    "family_history_hypertension": "family history of high blood pressure",
    "hypertensive": "diagnosed high blood pressure",
    "cardiovascular_disease": "heart disease history",
    "stroke": "stroke history",
}

# Proposal 1.2.2: separate what a person can work on from what they cannot change.
# Age, sex and family history give context only - never advice to "change" them.
FACTOR_TYPE = {
    "age": "not modifiable",
    "sex_male": "not modifiable",
    "family_history_diabetes": "not modifiable",
    "family_history_hypertension": "not modifiable",
    "bmi": "modifiable",
    "systolic_bp": "modifiable",
    "diastolic_bp": "modifiable",
    "pulse_rate": "modifiable",
    "glucose_mmol": "modifiable",
    "hypertensive": "medical history",
    "cardiovascular_disease": "medical history",
    "stroke": "medical history",
}


def _predict_fn(bundle):
    """predict_proba that accepts plain arrays, as SHAP and LIME pass them."""
    model, features = bundle["model"], bundle["features"]
    return lambda x: model.predict_proba(pd.DataFrame(x, columns=features))


def _factor_row(feature, value, weight, key) -> dict:
    return {
        "feature": feature,
        "readable": READABLE.get(feature, feature),
        "factor_type": FACTOR_TYPE.get(feature, "other"),
        "value": round(float(value), 2),
        key: float(weight),
        "direction": "increases risk" if weight > 0 else "decreases risk",
    }


def shap_explain(patient: dict, top_k: int | None = None) -> list[dict]:
    """SHAP assigns each feature the share of the prediction it is responsible for.

    A positive value pushed the risk UP, a negative value pushed it DOWN.
    These are contributions to THIS MODEL's output - not proof of medical cause.
    Calibration is monotonic, so it does not change any factor's direction.
    """
    import shap

    top_k = top_k or CFG["explain"]["top_k"]
    bundle = load_bundle(choose_feature_set(patient))
    X, _ = to_frame(patient, bundle["features"], bundle["fill_values"])

    if bundle["model_name"] in ("random_forest", "xgboost"):
        values = shap.TreeExplainer(bundle["model"]).shap_values(X)
    else:  # model-agnostic path (logistic regression pipeline)
        explainer = shap.Explainer(lambda x: _predict_fn(bundle)(x)[:, 1], bundle["background"])
        values = explainer(X).values

    values = np.array(values)
    # 3-D shape is (samples, features, classes)
    values = values[0, :, -1] if values.ndim == 3 else values[0]
    rows = [
        _factor_row(f, X.iloc[0][f], s, "shap")
        for f, s in zip(bundle["features"], values, strict=True)
    ]
    rows.sort(key=lambda r: abs(r["shap"]), reverse=True)
    return rows[:top_k]


def lime_explain(patient: dict, top_k: int | None = None, seed: int | None = None) -> dict:
    """LIME fits a simple linear model around this one patient to approximate
    the complex model locally. It is model-agnostic, so it acts as a cross-check
    on SHAP rather than a repeat of it. `fidelity` is the R^2 of that local fit:
    a low value means the local explanation should not be trusted much."""
    from lime.lime_tabular import LimeTabularExplainer

    top_k = top_k or CFG["explain"]["top_k"]
    seed = CFG["preprocess"]["random_state"] if seed is None else seed
    bundle = load_bundle(choose_feature_set(patient))
    features = bundle["features"]
    X, _ = to_frame(patient, features, bundle["fill_values"])

    explainer = LimeTabularExplainer(
        training_data=bundle["lime_background"].to_numpy(),
        feature_names=features,
        class_names=["No diabetes", "Diabetes risk"],
        mode="classification",
        random_state=seed,
    )
    exp = explainer.explain_instance(
        X.to_numpy()[0],
        _predict_fn(bundle),
        num_features=top_k,
        num_samples=CFG["explain"]["lime_num_samples"],
    )
    factors = []
    for rule, weight in exp.as_list():
        # Longest name first so "bmi" never matches inside another feature name.
        base = next((f for f in sorted(features, key=len, reverse=True) if f in rule), rule)
        factors.append({"rule": rule, **_factor_row(base, X.iloc[0][base], weight, "weight")})
    return {"factors": factors, "fidelity": round(float(exp.score), 4), "seed": seed}


def agreement(shap_rows, lime_rows) -> dict:
    """How many of the top factors both methods agree on.

    Disagreement is a finding worth reporting, not a bug: the two methods
    answer slightly different questions.
    """
    s = {r["feature"] for r in shap_rows}
    lm = {r["feature"] for r in lime_rows}
    overlap = s & lm
    ratio = round(len(overlap) / max(len(s), 1), 2)
    return {
        "shap_top": sorted(s),
        "lime_top": sorted(lm),
        "shared": sorted(overlap),
        "overlap_ratio": ratio,
        "meets_target": ratio >= CFG["explain"]["agreement_target"],
    }


def explanation_quality(agree: dict, fidelity: float) -> str:
    """Proposal 3.4.3: weak agreement or a poor LIME fit triggers a warning."""
    if agree["meets_target"] and fidelity >= CFG["explain"]["lime_fidelity_min"]:
        return "consistent"
    return "check: SHAP and LIME agree weakly or the LIME fit is poor; treat factors with care"


def narrate(prediction: dict, shap_rows: list[dict]) -> str:
    up = [r for r in shap_rows if r["shap"] > 0]
    down = [r for r in shap_rows if r["shap"] < 0]
    can_work_on = [r["readable"] for r in up if r["factor_type"] == "modifiable"][:3]
    context = [r["readable"] for r in up if r["factor_type"] != "modifiable"][:3]
    lines = [f"Your estimated risk band is {prediction['risk_category']}."]
    if can_work_on:
        lines.append("Factors you can work on that raised it: " + ", ".join(can_work_on) + ".")
    if context:
        lines.append("Background factors that raised it: " + ", ".join(context) + ".")
    if down:
        lines.append("Factors that lowered it: " + ", ".join(r["readable"] for r in down[:2]) + ".")
    if not prediction["data_complete"]:
        missing = ", ".join(READABLE.get(f, f) for f in prediction["imputed_fields"])
        lines.append(f"Not provided, so a typical value was used: {missing}.")
    if prediction["referral"]:
        lines.append(prediction["referral"])
    lines.append(
        "These are contributions to the model's estimate, not medical causes. "
        "Discuss any concerns with a healthcare professional."
    )
    return " ".join(lines)


def explain_patient(patient: dict) -> dict:
    prediction = predict_risk(patient)
    if prediction["status"] != "ok":
        return {"prediction": prediction}
    shap_rows = shap_explain(patient)
    lime = lime_explain(patient)
    agree = agreement(shap_rows, lime["factors"])
    return {
        "prediction": prediction,
        "shap": shap_rows,
        "lime": lime["factors"],
        "lime_fidelity": lime["fidelity"],
        "agreement": agree,
        "explanation_quality": explanation_quality(agree, lime["fidelity"]),
        "explanation_text": narrate(prediction, shap_rows),
    }


if __name__ == "__main__":
    import json

    result = explain_patient(EXAMPLE_PATIENT)
    print(json.dumps(result["prediction"], indent=2))
    print("\nSHAP top factors:")
    for r in result["shap"]:
        print(
            f"  {r['readable']:<38} value={r['value']:<7} shap={r['shap']:+.4f}  "
            f"{r['direction']:<15} ({r['factor_type']})"
        )
    print(f"\nLIME top factors (local fit R^2 = {result['lime_fidelity']}):")
    for r in result["lime"]:
        print(f"  {r['rule']:<42} weight={r['weight']:+.4f}")
    agree = result["agreement"]
    print(f"\nAgreement: {agree['overlap_ratio']} shared={agree['shared']}")
    print(f"Explanation quality: {result['explanation_quality']}")
    print(f"\n{result['explanation_text']}")
