# `c3_risk_xai` — C3 Multi-Factor Diabetic Risk Profiling & XAI

> Research prototype. Outputs are estimates and predictions, not diagnoses.

| | |
|---|---|
| Port | 8003 |
| Postgres schema | `c3` |
| Health | `GET /health` |
| Placeholder route | `POST /v1/risk/assess` (returns `501 Not Implemented`) |
| Gateway prefix | `/api/v1/risk/*` |

Run locally from the repository root:

```bash
uv sync
uv run uvicorn c3_risk_xai.main:app --reload --port 8003
uv run pytest server/services/c3_risk_xai
```

## Component details

Copied from `docs/SETUP_PROMPT.md` section 1a.

### C3 — Multi-Factor Diabetic Risk Profiling & XAI (Rajapaksha R.M.L.I)

**TAF tasks:**

1. Design the patient risk-profile schema: physical activity, smoking, medication history, BP, cholesterol, kidney and liver disease, and body-weight changes.
2. Develop a multi-factor risk engine combining clinical and lifestyle inputs with food data.
3. Implement SHAP and LIME explainability over the prediction models.
4. Build an adaptive Diabetic Health Score (DHS) that evolves with patient behaviour.
5. Validate recommendations through domain expert review and a user study.

**Novelty (TAF):**

- A multi-factor diabetic risk profiling engine for the Sri Lankan context that goes beyond food.
- Transparent SHAP/LIME explanations per prediction. Recommendations come from clinician-reviewed templates.
- A dynamic DHS integrating dietary quality, activity, adherence and clinical risk markers.

**Data:**

| Purpose | Source (TAF) | Status |
|---|---|---|
| Risk factors | Structured patient questionnaires, collected with informed consent | BRFSS 2015 (secondary) for now. Sri Lankan data (WHO STEPS, SLHAS) planned. Primary questionnaire data only after ethics approval. |
| Food and glycemic inputs | C1 and C2 outputs | Via contract |
| Clinical thresholds | Ministry of Health Sri Lanka, National Guideline for Management of Diabetes (2021), and Sri Lanka College of Endocrinologists Clinical Practice Guideline – Diabetes (2025). The 'SLMA/SHRI 2019' guideline in the TAF could not be found, so it is not used. | Reference only |

**Inputs and outputs:**

- Inputs: the risk profile, plus C1 nutrition and C2 forecast and risk score.
- Outputs: an estimated risk level, the DHS, and explanations per prediction.
- Consumer: the client, through the gateway.

**Decisions:**

- Data approach: BRFSS 2015 (secondary) for now. Sri Lankan data (WHO STEPS, SLHAS) planned. Primary questionnaire data only after ethics approval.
- **Update (2026-10-10, C3 owner):** BRFSS was replaced by South Asian data only: DiaBD and the Narsingdi hospital dataset (Bangladesh, CC BY 4.0), plus synthetic training augmentation. See "Implementation (PP1)" below and `docs/data_README.md`.
- C3 stores the C1/C2 results it receives in its own c3 schema, so it can use several days of data, not just one meal.

**Open items:**

- The risk-profile schema fields and units. These become a contract.
- The expert reviewer and the user-study plan.

---

## Implementation (PP1)

> Research prototype. Produces a statistical risk estimate to support self-management.
> It does not diagnose diabetes and is not a medical device.

| | |
|---|---|
| **Input** | Age, sex, BMI, blood pressure, pulse, optional blood glucose, family and medical history |
| **Processing** | Validation → completeness check → model choice (with / without glucose) → classifier → calibration → SHAP + LIME |
| **Output** | Low / Moderate / High band, calibrated probability, ranked factors (modifiable vs not), SHAP-LIME agreement, plain-language summary, referral note |

**Function 1 - risk prediction** (`src/c3_risk_xai/ml/predict.py`)
- Rejects impossible values.
- Returns `insufficient_data` with no band when age, BMI or blood pressure is missing.
- Fills other gaps with training medians and lists them.
- Uses the glucose model only when a glucose result is given.
- Adds a referral note to High results.

**Function 2 - explainable risk analysis** (`src/c3_risk_xai/ml/explain.py`)
- SHAP contributions and a LIME local surrogate for the same prediction.
- Top-5 agreement, LIME fit (R²) and an explanation-quality flag.
- Modifiable vs non-modifiable factors and a plain-language summary.

### API (client -> gateway :8000 -> C3 :8003)

| Client calls | C3 route | Answer |
|---|---|---|
| `POST /api/v1/risk/assess` | `POST /v1/risk/assess` | 200 with `status` `ok` / `insufficient_data` / `invalid_input`; 422 bad types; 503 models not loaded |
| `GET /api/v1/risk/status` | `GET /v1/risk/status` | `{"model_loaded": ..., "models": ...}` |

Request and response shapes: `docs/contract_proposal.md` (a proposal until the team agrees it in `contracts/`). The raw probability and band cut-offs are only returned in research mode (`C3_RESEARCH_MODE=true` and `?debug=true`), never to patients.

Layers: `api/routes.py` (thin) -> `services/risk_service.py` (the only layer that imports `ml/`) -> `ml/` (plain Python). `ml/dataprep/` is offline code, used only by `training/` and tests. `tests/test_architecture.py` enforces these rules.

**Client.** The Flutter app (`client/mobile_app/lib/features/risk_profile/`) is the only client: the seven Module 3 screens (DHS, health and lifestyle info, analysis, result, AI explanation, recommendations, what-if). It calls the gateway only and holds no model logic. The Streamlit demo was retired (supervisors require Flutter).

**Also in PP1:** provisional Diabetic Health Score and template recommendations (`ml/dhs.py`, `ml/recommend.py`, `config/dhs.yaml`); PostgreSQL schema `c3` with history, deletion and audit log (`db/`, `migrations/`, `docs/database.md`). PP1 pack: `docs/pp1/`.

### Results (real test set: 1,058 Bangladeshi adults never used in training)

| Model | Selected | 5-fold CV ROC-AUC | Test ROC-AUC | Test PR-AUC (base rate 0.065) |
|---|---|---|---|---|
| Without glucose | logistic regression | 0.814 | 0.779 | 0.220 |
| With glucose | random forest | 0.871 | 0.853 | 0.341 |

Risk bands on the real test set (with glucose): Low 1.1% diabetic, Moderate 7.3%, High 29.0%.
Median SHAP-LIME top-5 overlap over 30 test patients: 80% (proposal target 60%).
Accuracy is not a headline metric: only 6.5% are diabetic.

### Run (from the repository root)

```powershell
uv sync
uv run python server/services/c3_risk_xai/training/external_data.py          # download data
uv run python -m c3_risk_xai.ml.dataprep.south_asia_dataset                   # clean + harmonise
uv run python -m c3_risk_xai.ml.dataprep.data_loader                          # inspect
uv run python server/services/c3_risk_xai/training/train.py                   # CV, calibration, bands, save models
uv run python -m c3_risk_xai.ml.evidence                                      # figures + explanation quality
uv run python server/services/c3_risk_xai/training/experiment_south_asia.py  # synthetic + second-site experiment
uv run python -m c3_risk_xai.ml.predict                                       # Function 1 demo
uv run python -m c3_risk_xai.ml.explain                                       # Function 2 demo
uv run pytest server/services/c3_risk_xai -v                                  # tests (no data needed)
.\scripts\dev.ps1                                                             # gateway + C1-C4 services
.\server\services\c3_risk_xai\scripts\demo.ps1 -Research                    # C3 + gateway, one command
.\server\services\c3_risk_xai\scripts\demo_phone.ps1                       # ... plus the app in a phone window
```

### Where things live

```
server/services/c3_risk_xai/
├── config.yaml                 all settings; paths are relative to the repo root
├── src/c3_risk_xai/
│   ├── main.py  settings.py  schemas.py
│   ├── api/routes.py           thin FastAPI routes
│   ├── services/risk_service.py  orchestration; the only layer that imports ml/
│   ├── db/                     stub (c3 schema, later)
│   └── ml/                     config, preprocess, modeling, predict (FUNCTION 1),
│       │                       explain (FUNCTION 2), evidence
│       └── dataprep/           data_loader, south_asia_dataset, synthetic (offline)
├── training/                   external_data.py, train.py, experiment_south_asia.py
├── scripts/                    demo.ps1, demo_phone.ps1 (one-command demo)
├── migrations/, alembic.ini    PostgreSQL schema c3
├── tests/                      pipeline, service, API and architecture tests (no data needed)
└── docs/                       data dictionary, architecture, requirements, test plan,
                                risk register, diary, AI usage log, demo script, figures/,
                                contract_proposal, gateway_pr_note, ci_pr_note
data/c3/                        (repo root, gitignored) raw/, processed/, models/, outputs/
```

### Scope

**PP1:** risk schema, South Asian data pipeline, synthetic augmentation, three-model comparison
with cross-validation, calibration, data-driven risk bands, Function 1, Function 2,
explanation-quality evaluation, demo UI, tests, documentation.

**Done after PP1 planning:** `POST /v1/risk/assess` and `GET /v1/risk/status`.

**PP2:** agree contracts `patient_risk_profile` and `risk_assessment` in `contracts/`,
finish the C3 Flutter screens, adaptive DHS, C1/C2 inputs, clinician-reviewed recommendations,
Sri Lankan questionnaire data after ethics approval, expert review and user study.
