# Component 3 - Multi-Factor Diabetic Risk Profiling & Explainable AI

Part of **J26-IT-352, Personalized AI Diabetes Care System for Sri Lankan Patients**
Rajapaksha R.M.L.I (IT23315846) · Branch `c3_lochana`

> Research prototype. Produces a statistical risk estimate to support
> self-management. **It does not diagnose diabetes and is not a medical device.**

## What this component does

| | |
|---|---|
| **Input** | Patient risk factors: age, sex, BMI, blood pressure, pulse, optional blood glucose, family and medical history |
| **Processing** | Validation → completeness check → model choice (with / without glucose) → classifier → calibration → SHAP + LIME |
| **Output** | Low / Moderate / High risk band, calibrated probability, ranked factors (modifiable vs not), SHAP-LIME agreement, plain-language summary, referral note |

### Function 1 - Multi-factor risk prediction (`src/predict.py`)
- Rejects impossible values.
- Returns `insufficient_data` with **no band** when age, BMI or blood pressure is missing.
- Fills other gaps with training medians and lists them.
- Uses the glucose model only when a glucose result is given.
- Outputs a calibrated probability, a data-driven risk band and a referral note for High.

### Function 2 - Explainable risk analysis (`src/explain.py`)
- SHAP contributions and a LIME local surrogate for the same prediction.
- Top-5 agreement between the two, plus LIME local fit (R²).
- An explanation-quality flag.
- Factors split into modifiable / not modifiable / medical history.
- A plain-language summary.

## Results (real test set: 1,058 Bangladeshi adults never used in training)

| Model | Selected | 5-fold CV ROC-AUC | Test ROC-AUC | Test PR-AUC (base rate 0.065) |
|---|---|---|---|---|
| Without glucose | logistic regression | 0.814 | 0.779 | 0.220 |
| With glucose | random forest | 0.871 | 0.853 | 0.341 |

Risk bands on the real test set (with glucose): Low 1.1% diabetic · Moderate 7.3% ·
High 29.0%. Explanations over 30 test patients: median SHAP-LIME top-5 overlap 80%,
which meets the proposal's 60% target. Full numbers are in `outputs/reports/`, and
the figures are in `outputs/figures/`.

Accuracy is not a headline metric. Only 6.5% of people are diabetic, so a model
that always answers "no" would score 93.5%.

## Quick start (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python -m src.external_data          # download the two Bangladesh datasets
python -m src.south_asia_dataset     # harmonise into one table
python -m src.data_loader            # inspect it
python -m src.train                  # CV, model choice, calibration, bands, save models
python -m src.evidence               # figures + explanation-quality report
python -m src.experiment_south_asia  # real vs real+synthetic vs synthetic, second site
python -m src.predict                # Function 1 demo
python -m src.explain                # Function 2 demo
python -m pytest -v                  # 17 tests, run without the dataset
streamlit run app/streamlit_app.py   # demo UI
```

## Repository layout

```
├── config.yaml               all settings in one place
├── data/                     raw and processed data (never committed)
├── docs/                     data dictionary, architecture, requirements,
│                             test plan, risk register, diary, AI usage log
├── src/
│   ├── external_data.py      download with provenance manifest
│   ├── south_asia_dataset.py harmonise DiaBD + Narsingdi, plausibility checks
│   ├── data_loader.py        load + inspect
│   ├── preprocess.py         leakage-safe split
│   ├── synthetic.py          Gaussian copula synthetic generator
│   ├── train.py              CV, model choice, calibration, risk bands
│   ├── predict.py            FUNCTION 1
│   ├── explain.py            FUNCTION 2
│   ├── evidence.py           figures + explanation quality
│   └── experiment_south_asia.py  synthetic and second-site experiments
├── app/streamlit_app.py      demo interface
├── tests/                    automated tests (stand-in models, no data needed)
├── models/                   saved models (not committed)
└── outputs/                  figures and reports
```

## Dataset

Only South Asian data is used. It all comes from Bangladesh and is licensed CC BY 4.0.
- **DiaBD**: 5,288 adults, 6.5% diabetic. Used for training and testing.
- **Narsingdi hospital**: 496 unique patients. Used as a second-site check.
- **Synthetic rows**: generated from the training rows only, and used only to
  augment training.

No open Sri Lankan individual-level data exists, so these are **Bangladesh
findings, never Sri Lankan findings**. See `data/README.md` and
`docs/data_dictionary.md`.

## Scope

**In PP1:** risk schema, South Asian data pipeline, synthetic augmentation,
three-model comparison with cross-validation, calibration, data-driven risk bands,
Function 1, Function 2, explanation-quality evaluation, demo UI, tests, documentation.

**PP2:** adaptive DHS, C1/C2 integration, FastAPI service in
`server/services/c3_risk_xai`, clinician-reviewed recommendations, Sri Lankan
questionnaire data (after ethics approval), expert review and user study.
