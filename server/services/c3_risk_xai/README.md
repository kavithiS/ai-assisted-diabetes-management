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
- C3 stores the C1/C2 results it receives in its own c3 schema, so it can use several days of data, not just one meal.

**Open items:**

- The risk-profile schema fields and units. These become a contract.
- The expert reviewer and the user-study plan.
