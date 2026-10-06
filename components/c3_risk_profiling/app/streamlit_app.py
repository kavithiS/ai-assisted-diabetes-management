"""PP1 demo interface.

Run from the project root:
    streamlit run app/streamlit_app.py

Streamlit was chosen over React for the PP1 prototype because the panel is
assessing the risk engine and the explanations, not front-end work. The group's
real front end is Component 4's Flutter app; this is a research demo only.
"""
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.explain import explain_patient            # noqa: E402
from src.predict import EXAMPLE_PATIENT            # noqa: E402

st.set_page_config(page_title="Diabetic Risk Profiling", layout="wide")
st.title("Multi-Factor Diabetic Risk Profiling with Explainable AI")
st.caption("Component 3 research prototype - J26-IT-352. Not a medical device.")

st.warning("Research prototype. Produces a statistical risk estimate for "
           "self-management support only. It does not diagnose diabetes and "
           "does not replace professional medical assessment.")

with st.sidebar:
    st.header("Patient information")
    patient = dict(EXAMPLE_PATIENT)
    patient["Age"] = st.slider("Age group (1 = 18-24 ... 13 = 80+)", 1, 13, 9)
    patient["Sex"] = 1 if st.radio("Sex", ["Female", "Male"], index=1) == "Male" else 0
    patient["BMI"] = st.number_input("BMI", 12.0, 60.0, 29.4, 0.1)
    patient["HighBP"] = int(st.checkbox("Diagnosed high blood pressure", True))
    patient["HighChol"] = int(st.checkbox("Diagnosed high cholesterol", True))
    patient["Smoker"] = int(st.checkbox("Smoked 100+ cigarettes in lifetime"))
    patient["PhysActivity"] = int(st.checkbox("Physical activity in past 30 days"))
    patient["HeartDiseaseorAttack"] = int(st.checkbox("Heart disease history"))
    patient["Stroke"] = int(st.checkbox("Stroke history"))
    patient["DiffWalk"] = int(st.checkbox("Difficulty walking"))
    patient["GenHlth"] = st.select_slider(
        "Self-rated general health", [1, 2, 3, 4, 5], value=3,
        format_func=lambda v: {1: "Excellent", 2: "Very good", 3: "Good",
                               4: "Fair", 5: "Poor"}[v])
    run = st.button("Assess risk", type="primary", use_container_width=True)

if run:
    with st.spinner("Running model and generating explanations..."):
        result = explain_patient(patient)
    pred = result["prediction"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Estimated risk", f"{pred['risk_percent']}%")
    c2.metric("Risk band", pred["risk_category"])
    c3.metric("Data complete", "Yes" if pred["data_complete"] else "No")
    st.progress(min(pred["risk_probability"], 1.0))

    st.subheader("Why this result - SHAP")
    st.caption("Each value is this feature's contribution to the model output.")
    st.dataframe([{"Factor": r["readable"], "Patient value": r["value"],
                   "Contribution": round(r["shap"], 4), "Effect": r["direction"]}
                  for r in result["shap"]], use_container_width=True)

    st.subheader("Cross-check - LIME")
    st.dataframe([{"Rule": r["rule"], "Weight": round(r["weight"], 4),
                   "Effect": r["direction"]} for r in result["lime"]],
                 use_container_width=True)

    agree = result["agreement"]
    st.info(f"SHAP and LIME agree on {int(agree['overlap_ratio'] * 100)}% of the "
            f"top factors: {', '.join(agree['shared']) or 'none'}. "
            "The two methods answer different questions, so partial disagreement "
            "is expected and is reported rather than hidden.")

    st.subheader("Plain-language summary")
    st.write(result["explanation_text"])
else:
    st.info("Set the patient details in the sidebar, then select Assess risk.")
