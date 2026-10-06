"""FUNCTION 2 - Explainable risk analysis with SHAP and LIME.

INPUT      a patient record + the trained model
PROCESSING SHAP (Shapley contributions) and LIME (local surrogate model)
OUTPUT     ranked contributing factors + a plain-language explanation
           + an agreement check between the two methods

Run:
    python -m src.explain
"""
import numpy as np
import pandas as pd
from .config import CFG, abs_path
from .predict import load_model, to_frame, predict_risk, EXAMPLE_PATIENT

# Plain-language names so the output is readable by a non-technical user.
READABLE = {
    "HighBP": "high blood pressure", "HighChol": "high cholesterol",
    "CholCheck": "cholesterol check history", "BMI": "body mass index",
    "Smoker": "smoking history", "Stroke": "history of stroke",
    "HeartDiseaseorAttack": "heart disease history",
    "PhysActivity": "physical activity", "Fruits": "fruit intake",
    "Veggies": "vegetable intake", "HvyAlcoholConsump": "heavy alcohol use",
    "AnyHealthcare": "healthcare coverage", "NoDocbcCost": "cost barrier to care",
    "GenHlth": "self-rated general health", "MentHlth": "poor mental health days",
    "PhysHlth": "poor physical health days", "DiffWalk": "difficulty walking",
    "Sex": "sex", "Age": "age group", "Education": "education level",
    "Income": "income level",
}


def _background(features, n):
    """SHAP needs reference data to answer 'compared with what?'.
    Here we use a sample of the training split."""
    train = pd.read_csv(abs_path("data/processed/train.csv"))
    return train.drop(columns=["target"])[features].sample(
        min(n, len(train)), random_state=CFG["preprocess"]["random_state"])


def shap_explain(patient: dict, top_k: int | None = None) -> list[dict]:
    """SHAP assigns each feature the share of the prediction it is responsible for.

    A positive value pushed the risk UP, a negative value pushed it DOWN.
    These are contributions to THIS MODEL's output - not proof of medical cause.
    """
    import shap
    top_k = top_k or CFG["explain"]["top_k"]
    model, features = load_model()
    X, _ = to_frame(patient, features)
    bg = _background(features, CFG["explain"]["background_samples"])

    try:  # fast exact path for tree models
        explainer = shap.TreeExplainer(model)
        values = explainer.shap_values(X)
    except Exception:  # model-agnostic fallback (e.g. logistic regression)
        explainer = shap.Explainer(model.predict_proba, bg)
        values = explainer(X).values

    values = np.array(values)
    if values.ndim == 3:            # (samples, features, classes)
        values = values[0, :, -1]
    else:
        values = values[0]

    rows = [{"feature": f,
             "readable": READABLE.get(f, f),
             "value": float(X.iloc[0][f]),
             "shap": float(s),
             "direction": "increases risk" if s > 0 else "decreases risk"}
            for f, s in zip(features, values)]
    rows.sort(key=lambda r: abs(r["shap"]), reverse=True)
    return rows[:top_k]


def lime_explain(patient: dict, top_k: int | None = None) -> list[dict]:
    """LIME fits a simple linear model around this one patient to approximate
    the complex model locally. It is model-agnostic, so it acts as a cross-check
    on SHAP rather than a repeat of it."""
    from lime.lime_tabular import LimeTabularExplainer
    top_k = top_k or CFG["explain"]["top_k"]
    model, features = load_model()
    X, _ = to_frame(patient, features)
    bg = _background(features, 500)

    explainer = LimeTabularExplainer(
        training_data=bg.values, feature_names=features,
        class_names=["No diabetes", "Diabetes risk"], mode="classification",
        random_state=CFG["preprocess"]["random_state"])
    exp = explainer.explain_instance(X.values[0], model.predict_proba,
                                     num_features=top_k)
    out = []
    for rule, weight in exp.as_list():
        base = next((f for f in features if f in rule), rule)
        out.append({"rule": rule, "feature": base,
                    "readable": READABLE.get(base, base),
                    "weight": float(weight),
                    "direction": "increases risk" if weight > 0 else "decreases risk"})
    return out


def agreement(shap_rows, lime_rows) -> dict:
    """How many of the top factors both methods agree on.

    Disagreement is a finding worth reporting, not a bug: the two methods
    answer slightly different questions.
    """
    s = {r["feature"] for r in shap_rows}
    l = {r["feature"] for r in lime_rows}
    overlap = s & l
    return {"shap_top": sorted(s), "lime_top": sorted(l),
            "shared": sorted(overlap),
            "overlap_ratio": round(len(overlap) / max(len(s), 1), 2)}


def narrate(prediction: dict, shap_rows: list[dict]) -> str:
    up = [r for r in shap_rows if r["shap"] > 0][:3]
    down = [r for r in shap_rows if r["shap"] < 0][:2]
    lines = [f"Estimated risk: {prediction['risk_percent']}% "
             f"({prediction['risk_category']} band)."]
    if up:
        lines.append("Factors that raised this estimate most: "
                     + ", ".join(r["readable"] for r in up) + ".")
    if down:
        lines.append("Factors that lowered it: "
                     + ", ".join(r["readable"] for r in down) + ".")
    lines.append("These are contributions to the model's output, not medical causes. "
                 "Discuss any concerns with a healthcare professional.")
    return " ".join(lines)


def explain_patient(patient: dict) -> dict:
    prediction = predict_risk(patient)
    shap_rows = shap_explain(patient)
    lime_rows = lime_explain(patient)
    return {"prediction": prediction,
            "shap": shap_rows,
            "lime": lime_rows,
            "agreement": agreement(shap_rows, lime_rows),
            "explanation_text": narrate(prediction, shap_rows)}


if __name__ == "__main__":
    import json
    result = explain_patient(EXAMPLE_PATIENT)
    print(json.dumps(result["prediction"], indent=2))
    print("\nSHAP top factors:")
    for r in result["shap"]:
        print(f"  {r['readable']:<32} value={r['value']:<6} "
              f"shap={r['shap']:+.4f}  {r['direction']}")
    print("\nLIME top factors:")
    for r in result["lime"]:
        print(f"  {r['rule']:<38} weight={r['weight']:+.4f}")
    print(f"\nAgreement: {result['agreement']['overlap_ratio']} "
          f"shared={result['agreement']['shared']}")
    print(f"\n{result['explanation_text']}")
