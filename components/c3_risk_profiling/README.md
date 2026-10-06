# Component 3 - Multi-Factor Diabetic Risk Profiling & Explainable AI

Part of **J26-IT-352, Personalized AI Diabetes Care System for Sri Lankan Patients**
Rajapaksha R.M.L.I (IT23315846) · Branch `c3_lochana`

> Research prototype. Produces a statistical risk estimate to support
> self-management. **It does not diagnose diabetes and is not a medical device.**

## What this component does

| | |
|---|---|
| **Input** | Patient risk factors - demographics, anthropometrics, lifestyle, medical history, clinical flags |
| **Processing** | Validation → preprocessing → trained classifier → SHAP + LIME |
| **Output** | Risk probability, risk band, ranked contributing factors, plain-language explanation |

### Function 1 - Multi-factor risk prediction (`src/predict.py`)
Patient record → validated and aligned features → trained model → probability
and Low/Moderate/High band, with missing fields reported rather than hidden.

### Function 2 - Explainable risk analysis (`src/explain.py`)
Prediction → SHAP contributions + LIME local surrogate → ranked factors,
an agreement check between the two methods, and a readable summary.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Get the dataset - see data/README.md
python -m src.data_loader          # inspect it
python -m src.preprocess           # clean and split
python -m src.train                # train and compare three models
python -m src.predict              # Function 1
python -m src.explain              # Function 2
pytest -v                          # run the tests
streamlit run app/streamlit_app.py # demo UI
```

## Repository layout

```
├── config.yaml          all settings in one place
├── data/                raw and processed data (never committed)
├── docs/                data dictionary, architecture, requirements,
│                        test plan, risk register, diary, AI usage log
├── src/                 the pipeline
│   ├── data_loader.py   load + integrity checks
│   ├── preprocess.py    clean, binarise, leakage-safe split
│   ├── train.py         train and compare models
│   ├── predict.py       FUNCTION 1
│   └── explain.py       FUNCTION 2
├── app/streamlit_app.py demo interface
├── tests/               automated tests
├── models/              saved models (not committed)
└── outputs/             figures and reports
```

## Dataset

PP1 uses **CDC Diabetes Health Indicators (BRFSS 2015)** from UCI - 253,680 rows,
21 features, 3-class target. It is **US self-reported survey data**, used for
development and benchmarking only. Sri Lankan validation (WHO STEPS, SLHAS) and
NHANES are PP2 scope. See `data/README.md` and `docs/data_dictionary.md`.

## Scope

**In PP1:** risk schema, preprocessing pipeline, three-model comparison,
Function 1, Function 2, demo UI, tests, documentation.

**PP2:** adaptive DHS, C1/C2 integration, FastAPI service, recommendation layer,
Sri Lankan dataset validation, expert review and user study.
