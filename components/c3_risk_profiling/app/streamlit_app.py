"""PP1 demo interface.

Run from the project root:
    streamlit run app/streamlit_app.py

Streamlit was chosen over React for the PP1 prototype because the panel is
assessing the risk engine and the explanations, not front-end work. The group's
real front end is Component 4's Flutter app; this is a research demo only.
"""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.explain import explain_patient  # noqa: E402
from src.predict import EXAMPLE_PATIENT, LOW_RISK_PATIENT  # noqa: E402

REPORTS = ROOT / "outputs" / "reports"
FIGURES = ROOT / "outputs" / "figures"
BAND_COLOUR = {"Low": "#2e7d32", "Moderate": "#ef6c00", "High": "#c62828"}
PRESETS = {"Higher-risk example": EXAMPLE_PATIENT, "Lower-risk example": LOW_RISK_PATIENT}

st.set_page_config(page_title="C3 Diabetic Risk Profiling", layout="wide")
st.title("Multi-Factor Diabetic Risk Profiling with Explainable AI")
st.caption(
    "Component 3 research prototype - J26-IT-352 - Rajapaksha R.M.L.I. "
    "Trained on South Asian (Bangladesh) data. Not a medical device."
)
st.warning(
    "Research prototype. Produces a statistical risk estimate for self-management "
    "support only. It does not diagnose diabetes and does not replace professional "
    "medical assessment."
)


def load_json(name):
    path = REPORTS / name
    return json.loads(path.read_text()) if path.exists() else None


def patient_form() -> dict:
    """Sidebar inputs. A preset fills every field so the live demo is quick."""
    with st.sidebar:
        st.header("Patient information")
        preset = st.selectbox("Start from", ["Higher-risk example", "Lower-risk example"])
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
        run = st.button("Assess risk", type="primary", use_container_width=True)
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


def show_result(result):
    pred = result["prediction"]
    if pred["status"] == "insufficient_data":
        st.error(
            "Not enough information for a trustworthy estimate. Missing: "
            + ", ".join(pred["missing_critical_fields"])
        )
        return
    if pred["status"] == "invalid_input":
        st.error("Please check these values: " + "; ".join(pred["problems"]))
        return

    band = pred["risk_category"]
    c1, c2, c3 = st.columns(3)
    c1.markdown(
        f"<div style='background:{BAND_COLOUR[band]};color:white;padding:18px;"
        f"border-radius:10px;text-align:center'><div>Estimated risk band</div>"
        f"<div style='font-size:34px;font-weight:700'>{band}</div></div>",
        unsafe_allow_html=True,
    )
    model_label = (
        "Questionnaire + glucose"
        if pred["feature_set"] == "with_glucose"
        else ("Questionnaire only (no glucose)")
    )
    c2.metric("Model used", model_label, pred["model_used"].replace("_", " "))
    c3.metric("Data complete", "Yes" if pred["data_complete"] else "No")
    if pred["referral"]:
        st.error(pred["referral"])

    st.subheader("Plain-language summary")
    st.write(result["explanation_text"])

    left, right = st.columns(2)
    with left:
        st.subheader("Why - SHAP contributions")
        st.pyplot(factor_chart(result["shap"]))
        st.dataframe(
            pd.DataFrame(result["shap"])[["readable", "value", "factor_type", "direction"]].rename(
                columns={
                    "readable": "Factor",
                    "value": "Patient value",
                    "factor_type": "Type",
                    "direction": "Effect",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
    with right:
        st.subheader("Cross-check - LIME")
        st.dataframe(
            pd.DataFrame(result["lime"])[["rule", "weight", "direction"]].rename(
                columns={"rule": "Local rule", "weight": "Weight", "direction": "Effect"}
            ),
            hide_index=True,
            use_container_width=True,
        )
        agree = result["agreement"]
        st.metric("SHAP-LIME top-5 agreement", f"{int(agree['overlap_ratio'] * 100)}%")
        st.metric("LIME local fit (R²)", result["lime_fidelity"])
        quality = result["explanation_quality"]
        (st.success if quality == "consistent" else st.warning)(f"Explanation quality: {quality}")
        st.caption(
            "SHAP and LIME answer slightly different questions, so partial disagreement "
            "is expected and is reported rather than hidden."
        )

    with st.expander("Researcher view (not shown to patients)"):
        st.write(
            f"Calibrated probability: **{pred['risk_percent']}%**  |  band cut-offs: "
            f"Low < {pred['thresholds']['low_max']}, High >= {pred['thresholds']['high_min']}"
        )
        st.json(pred)


def evidence_tab():
    comparison = load_json("model_comparison.json")
    if not comparison:
        st.info("Run `python -m src.train` and `python -m src.evidence` first.")
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
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        bands = pd.DataFrame(info["models"][info["selected_model"]]["test_bands"])
        st.caption("Risk bands on the real test set (selected model)")
        st.dataframe(bands, hide_index=True, use_container_width=True)

    quality = load_json("explanation_quality.json")
    if quality:
        st.subheader("Explanation quality on 30 real test patients")
        st.dataframe(pd.DataFrame(quality).T, use_container_width=True)
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
            use_container_width=True,
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
        st.dataframe(pd.read_csv(schema), hide_index=True, use_container_width=True)


assess, evidence, data = st.tabs(["Risk assessment", "Model evidence", "Data & limitations"])
patient = patient_form()
with assess:
    if patient:
        with st.spinner("Running the model and generating explanations..."):
            show_result(explain_patient(patient))
    else:
        st.info("Choose a preset or enter patient details in the sidebar, then select Assess risk.")
with evidence:
    evidence_tab()
with data:
    data_tab()
