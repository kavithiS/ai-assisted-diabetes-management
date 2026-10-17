# mypy: ignore-errors
# Older ML code, not fully typed yet. Remove these two lines once it is (docs/ci_pr_note.md).
"""PP1 demo interface - a CLIENT of the C3 API, not part of the server.

It sends the patient profile to POST /api/v1/risk/assess through the gateway and shows
what comes back. It imports no C3 model code, so it proves the real client -> gateway ->
C3 path. Streamlit is for the PP1 demo only; the Flutter app is the real client, and
whether Streamlit is allowed for PP1 is an open question in CLAUDE.md.

Run from the repository root, with the gateway (:8000) and C3 (:8003) running
(for example via scripts/dev.ps1):
    uv run --package c3-risk-xai --extra demo streamlit run \
        server/services/c3_risk_xai/demo/streamlit_app.py

Set C3_DEMO_API_URL to point at a different gateway.
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

API_URL = os.environ.get("C3_DEMO_API_URL", "http://localhost:8000/api/v1/risk/assess")
SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[2]
# Read-only evidence files produced by training (the reports are gitignored).
REPORTS = REPO_ROOT / "data" / "c3" / "outputs" / "reports"
FIGURES = SERVICE_ROOT / "docs" / "figures"

# Label + icon + colour, so the band never relies on colour alone.
BAND_STYLE = {
    "Low": ("#2e7d32", "&#10003;"),
    "Moderate": ("#ef6c00", "&#9888;"),
    "High": ("#c62828", "&#9888;&#9888;"),
}
# Demo inputs only (not data): the same two example people used in the C3 docs.
PRESETS: dict[str, dict[str, Any]] = {
    "Higher-risk example": {
        "age": 58, "sex_male": 1, "bmi": 27.8, "systolic_bp": 150, "diastolic_bp": 95,
        "pulse_rate": 84, "glucose_mmol": 9.8, "family_history_diabetes": 1,
        "family_history_hypertension": 1, "hypertensive": 1,
        "cardiovascular_disease": 0, "stroke": 0,
    },
    "Lower-risk example": {
        "age": 29, "sex_male": 0, "bmi": 21.5, "systolic_bp": 112, "diastolic_bp": 72,
        "pulse_rate": 72, "glucose_mmol": 5.4, "family_history_diabetes": 0,
        "family_history_hypertension": 0, "hypertensive": 0,
        "cardiovascular_disease": 0, "stroke": 0,
    },
}  # fmt: skip

st.set_page_config(page_title="C3 Diabetic Risk Profiling", layout="wide")
st.title("Multi-Factor Diabetic Risk Profiling with Explainable AI")
st.caption(
    "Component 3 research prototype - J26-IT-352 - Rajapaksha R.M.L.I. "
    "Trained on South Asian (Bangladesh) data. Not a medical device. "
    f"Client of the C3 API at {API_URL}."
)
st.warning(
    "Research prototype. Produces a statistical risk estimate for self-management "
    "support only. It does not diagnose diabetes and does not replace professional "
    "medical assessment."
)


def call_api(patient: dict[str, Any], debug: bool = False) -> tuple[int, dict[str, Any]]:
    """POST the profile to the gateway. Returns (HTTP status, JSON body)."""
    body = {k: v for k, v in patient.items() if v is not None}
    url = API_URL + ("?debug=true" if debug else "")
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b"{}")


def load_json(name):
    path = REPORTS / name
    return json.loads(path.read_text()) if path.exists() else None


def patient_form() -> dict:
    """Sidebar inputs. A preset fills every field so the live demo is quick."""
    with st.sidebar:
        st.header("Patient information")
        preset = st.selectbox("Start from", list(PRESETS))
        p = PRESETS[preset]
        age = st.number_input("Age (years)", 18, 100, p["age"])
        sex = st.radio("Sex", ["Female", "Male"], index=p["sex_male"], horizontal=True)
        height = st.number_input("Height (cm)", 120.0, 210.0, 160.0, 0.5)
        weight = st.number_input("Weight (kg)", 30.0, 200.0, round(p["bmi"] * 1.6**2, 1), 0.5)
        bmi = weight / (height / 100) ** 2
        st.caption(f"BMI = {bmi:.1f}")
        sbp = st.number_input("Systolic BP (mmHg)", 70, 260, p["systolic_bp"])
        dbp = st.number_input("Diastolic BP (mmHg)", 40, 150, p["diastolic_bp"])
        pulse = st.number_input("Resting pulse (bpm)", 35, 200, p["pulse_rate"])
        has_glucose = st.checkbox("I have a recent blood glucose result", True)
        glucose = (
            st.number_input("Blood glucose (mmol/L)", 1.5, 40.0, float(p["glucose_mmol"]), 0.1)
            if has_glucose
            else None
        )
        st.subheader("History")
        flags = {
            "family_history_diabetes": "Parent or sibling with diabetes",
            "family_history_hypertension": "Parent or sibling with high BP",
            "hypertensive": "Diagnosed high blood pressure",
            "cardiovascular_disease": "Heart disease history",
            "stroke": "Stroke history",
        }
        values = {k: int(st.checkbox(label, bool(p[k]))) for k, label in flags.items()}
        run = st.button("Assess risk", type="primary", width="stretch")
    patient = {
        "age": age,
        "sex_male": int(sex == "Male"),
        "bmi": round(bmi, 2),
        "systolic_bp": sbp,
        "diastolic_bp": dbp,
        "pulse_rate": pulse,
        "glucose_mmol": glucose,
        **values,
    }
    return patient if run else None


def factor_chart(rows):
    labels = [r["readable"] for r in rows][::-1]
    values = [r["shap"] for r in rows][::-1]
    fig, ax = plt.subplots(figsize=(6, 0.5 * len(rows) + 1))
    ax.barh(labels, values, color=["#c62828" if v > 0 else "#1565c0" for v in values])
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("SHAP contribution (red raises, blue lowers the estimate)")
    fig.tight_layout()
    return fig


def show_result(patient: dict[str, Any]) -> None:
    try:
        code, result = call_api(patient)
    except (urllib.error.URLError, OSError) as err:
        st.error(
            f"The C3 API is not reachable at {API_URL} ({err}). Start the gateway and C3 "
            "(scripts/dev.ps1), then select Assess risk again to retry."
        )
        return
    if code == 503:
        st.error("C3 is running but its models are not loaded: " + str(result.get("detail")))
        return
    if code != 200:
        st.error(f"The API answered {code}: {result.get('detail', result)}")
        return
    if result["status"] == "insufficient_data":
        st.error(
            "Not enough information for a trustworthy estimate. Missing: "
            + ", ".join(result["missing_critical_fields"])
        )
        return
    if result["status"] == "invalid_input":
        st.error("Please check these values: " + "; ".join(result["problems"]))
        return

    band = result["risk_category"]
    colour, icon = BAND_STYLE[band]
    c1, c2, c3 = st.columns(3)
    c1.markdown(
        f"<div style='background:{colour};color:white;padding:18px;"
        f"border-radius:10px;text-align:center'><div>Estimated risk band</div>"
        f"<div style='font-size:34px;font-weight:700'>{icon} {band}</div></div>",
        unsafe_allow_html=True,
    )
    model_label = (
        "Questionnaire + glucose"
        if result["feature_set"] == "with_glucose"
        else ("Questionnaire only (no glucose)")
    )
    c2.metric("Model used", model_label, result["model_used"].replace("_", " "))
    c3.metric("Data complete", "Yes" if result["data_complete"] else "No")
    if result.get("referral"):
        st.error(result["referral"])
    st.caption(result["disclaimer"])

    explanation = result["explanation"]
    st.subheader("Plain-language summary")
    st.write(explanation["explanation_text"])

    left, right = st.columns(2)
    with left:
        st.subheader("Why - SHAP contributions")
        st.pyplot(factor_chart(explanation["shap"]))
        shap_table = pd.DataFrame(explanation["shap"])[
            ["readable", "value", "factor_type", "direction"]
        ].rename(
            columns={
                "readable": "Factor",
                "value": "Patient value",
                "factor_type": "Type",
                "direction": "Effect",
            }
        )
        st.dataframe(shap_table, hide_index=True, width="stretch")
    with right:
        st.subheader("Cross-check - LIME")
        st.dataframe(
            pd.DataFrame(explanation["lime"])[["rule", "weight", "direction"]].rename(
                columns={"rule": "Local rule", "weight": "Weight", "direction": "Effect"}
            ),
            hide_index=True,
            width="stretch",
        )
        agree = explanation["agreement"]
        st.metric("SHAP-LIME top-5 agreement", f"{int(agree['overlap_ratio'] * 100)}%")
        st.metric("LIME local fit (R²)", explanation["lime_fidelity"])
        quality = explanation["explanation_quality"]
        (st.success if quality == "consistent" else st.warning)(f"Explanation quality: {quality}")
        st.caption(
            "SHAP and LIME answer slightly different questions, so partial disagreement "
            "is expected and is reported rather than hidden."
        )

    with st.expander("Researcher view (not shown to patients)"):
        _, debug_result = call_api(patient, debug=True)
        debug = debug_result.get("debug")
        if debug:
            st.write(
                f"Calibrated probability: **{debug['risk_percent']}%**  |  band cut-offs: "
                f"Low < {debug['thresholds']['low_max']}, "
                f"High >= {debug['thresholds']['high_min']}"
            )
        else:
            st.info("The server is not in research mode (C3_RESEARCH_MODE), so no probability.")
        st.json(result)


def evidence_tab():
    comparison = load_json("model_comparison.json")
    if not comparison:
        st.info("No reports found in data/c3/outputs/reports. Run the training pipeline first.")
        return
    st.markdown(
        "All test numbers come from **1,058 real people never used in training**. "
        "Accuracy is not shown as a headline: only 6.5% of people are diabetic, so a "
        "model that always says *no* would score 93.5%."
    )
    for fs, info in comparison["feature_sets"].items():
        st.subheader(
            ("With glucose" if fs == "with_glucose" else "Without glucose")
            + f" - selected: {info['selected_model']}"
        )
        rows = []
        for name, m in info["models"].items():
            rows.append(
                {
                    "Model": name,
                    "CV ROC-AUC": m["cross_validation"]["roc_auc"],
                    "CV PR-AUC": m["cross_validation"]["pr_auc"],
                    "Test ROC-AUC": m["test"]["roc_auc"],
                    "Test PR-AUC": m["test"]["pr_auc"],
                    "Recall": m["test"]["recall_sensitivity"],
                    "Specificity": m["test"]["specificity"],
                    "Brier raw": m["test"]["brier"],
                    "Brier calibrated": m["test"]["brier_calibrated"],
                }
            )
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        bands = pd.DataFrame(info["models"][info["selected_model"]]["test_bands"])
        st.caption("Risk bands on the real test set (selected model)")
        st.dataframe(bands, hide_index=True, width="stretch")

    quality = load_json("explanation_quality.json")
    if quality:
        st.subheader("Explanation quality on 30 real test patients")
        st.dataframe(pd.DataFrame(quality).T, width="stretch")
        st.caption(
            "Proposal target: top-5 SHAP-LIME overlap >= 60%. "
            "Stability is measured across LIME random seeds."
        )

    experiment = load_json("south_asia_experiment.json")
    if experiment:
        st.subheader("Real vs real + synthetic vs synthetic-only (DiaBD test set)")
        res = pd.DataFrame(experiment["test_results"])
        st.dataframe(
            res[["scenario", "features", "model", "roc_auc", "pr_auc", "recall_sensitivity"]],
            hide_index=True,
            width="stretch",
        )
        st.caption(f"Synthetic fidelity: {experiment['synthetic_fidelity']}")

    st.subheader("Figures")
    for name in [
        "risk_bands.png",
        "roc_pr_with_glucose.png",
        "roc_pr_without_glucose.png",
        "calibration.png",
        "shap_summary_with_glucose.png",
        "shap_summary_without_glucose.png",
    ]:
        if (FIGURES / name).exists():
            st.image(str(FIGURES / name))


def data_tab():
    st.markdown(
        """
**Real data - South Asian only (Bangladesh, CC BY 4.0):**
- **DiaBD** (Mendeley m8cgwxs9s6, Data in Brief 2025): 5,288 adults, 6.5% diabetic.
  Used for training and testing.
- **Narsingdi hospital** (Mendeley rn9m3zb7nt): 496 unique patients after removing
  569 duplicate rows. Used as a second-site check.

**Synthetic data:** Gaussian copula fitted on the training rows only; used to augment
training, never in the test set; 0 exact copies of real people.

**No open Sri Lankan individual-level data exists** (SLDCS, SLHAS and WHO STEPS are on
request). Results are Bangladesh findings, never Sri Lankan findings.

**Known limitations**
- Schema coverage: medication, kidney/liver markers, lipids, diet, smoking, activity
  and weight change are not in any open South Asian dataset. They come from the
  Sri Lankan questionnaire (after ethics approval) and from C1/C2 in PP2.
- The model estimates current diabetes status from a cross-sectional survey, not
  future onset.
- Risk-band cut-offs are data-driven and pending clinical review.
- A model trained on one site transfers poorly to another hospital without glucose
  (see the experiment report), which is why local validation is planned.
"""
    )
    schema = REPORTS / "south_asia_schema.csv"
    if schema.exists():
        st.subheader("Feature schema and missingness")
        st.dataframe(pd.read_csv(schema), hide_index=True, width="stretch")


assess, evidence, data = st.tabs(["Risk assessment", "Model evidence", "Data & limitations"])
patient = patient_form()
with assess:
    if patient:
        with st.spinner("Calling the C3 API (model + SHAP + LIME)..."):
            show_result(patient)
    else:
        st.info("Choose a preset or enter patient details in the sidebar, then select Assess risk.")
with evidence:
    evidence_tab()
with data:
    data_tab()
