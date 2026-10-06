# Test plan - Component 3

Automated tests live in `tests/test_pipeline.py`. Run `pytest -v` from the
project root and screenshot the output into `outputs/reports/`.

**Fill in Actual Result and Status yourself after running the tests.
Never pre-fill results you have not observed.**

| ID | Feature | Input | Expected result | Actual | Status | Evidence |
|---|---|---|---|---|---|---|
| T01 | Data load | Raw CSV | 253,680 rows, 22 columns, 0 missing | | | terminal screenshot |
| T02 | Duplicate removal | Raw CSV | Duplicate count reported and removed | | | terminal screenshot |
| T03 | Train/test split | Processed data | Class balance preserved in both splits | | | terminal screenshot |
| T04 | Model training | Train split | Three models trained and saved | | | `models/` + JSON report |
| T05 | Prediction range | Example patient | Probability between 0 and 1 | | | pytest |
| T06 | Risk banding | p=0.10 / 0.50 / 0.90 | Low / Moderate / High | | | pytest |
| T07 | Missing fields | Partial record | `data_complete` is false, fields listed | | | pytest |
| T08 | Feature order | Example patient | Column order matches training | | | pytest |
| T09 | Directional sanity | Low-risk vs high-risk profile | High profile scores higher | | | pytest |
| T10 | Extreme values | BMI 12 and BMI 60 | No crash, valid probability | | | pytest |
| T11 | SHAP output | Example patient | 5 ranked factors with signed contributions | | | pytest + screenshot |
| T12 | LIME output | Example patient | 5 weighted local rules | | | pytest + screenshot |
| T13 | XAI agreement | Example patient | Overlap ratio computed and displayed | | | app screenshot |
| T14 | UI input validation | Out-of-range BMI | Rejected by the control, no crash | | | app screenshot |
| T15 | Disclaimer | Any prediction | Non-diagnostic warning always shown | | | app screenshot |
