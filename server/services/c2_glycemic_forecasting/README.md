# `c2_glycemic_forecasting` — C2 Glycemic Prediction & Risk Forecasting

> Research prototype. Outputs are estimates and predictions, not diagnoses.

| | |
|---|---|
| Port | 8002 |
| Postgres schema | `c2` |
| Health | `GET /health` |
| Placeholder route | `POST /v1/glucose/forecast` (returns `501 Not Implemented`) |
| Gateway prefix | `/api/v1/glucose/*` |

Run locally from the repository root:

```bash
uv sync
uv run uvicorn c2_glycemic_forecasting.main:app --reload --port 8002
uv run pytest server/services/c2_glycemic_forecasting
```

## Component details

Copied from `docs/SETUP_PROMPT.md` section 1a.

### C2 — Glycemic Prediction & Risk Forecasting (Jayamanna J.M.A.N.D)

**TAF tasks:**

1. Compile a Sri Lankan meal glycemic index reference dataset.
2. Engineer features from the nutritional profile, patient history and meal timing.
3. Train LSTM/GRU time-series models for 4-hour glucose forecasting.
4. Build an XGBoost dietary risk classifier and a composite risk-score algorithm.
5. Validate predictions against clinical glucose reference data.

**Novelty (TAF):**

- Personalised glucose trajectory forecasting using locally validated Sri Lankan meal GI profiles.
- A dynamic dietary risk score integrating meal timing, carbohydrate load and cumulative daily intake.

**Data:**

| Purpose | Source | Status |
|---|---|---|
| Glucose time-series and meal data for model development and validation | CGMacros | Confirmed C2 dataset |
| GI references | University of Sri Jayewardenepura GI references | Named in the TAF |
| Meal nutrition | C1 output | Via contract |

**Inputs and outputs:**

- Runtime inputs:
  - C1 meal nutrition
  - Meal timing
  - Patient-provided current/pre-meal blood glucose measurement
- Training inputs:
  - CGMacros meal/nutrition data
  - Pre-meal glucose
  - Post-meal glucose observations
  - Other approved contextual features where available
- Outputs:
  - A 4-hour predicted post-meal glucose trajectory
  - Measurable trajectory characteristics
  - A research-defined dietary risk score/category
  - Model/version metadata
- Consumers: C3 and the client, through the gateway.

**Decisions:**

- CGMacros is the confirmed dataset for C2 model development and validation.
- ShanghaiT2DM is NOT used as an independent external validation dataset.
- The runtime workflow requires the patient to provide their current/pre-meal glucose measurement before the meal.
- The current-glucose workflow is a supervisor-approved implementation decision and should not be described as a TAF requirement.
- No primary patient glucose data may be collected for research purposes without ethical clearance.
- CGMacros meal events should be aligned with glucose measurements to construct meal-centred prediction samples.
- Participant-aware train/validation/test splitting must be used to reduce participant-level data leakage.
- The XGBoost output is a research-defined dietary/postprandial risk measure and is not a clinical diagnosis.

**Open items:**

- Final C2 feature set.
- Final format and validation rules for the pre-meal glucose input.
- Final Sri Lankan GI reference source and licensing/access details.
- Final validation protocol and evaluation metrics.
