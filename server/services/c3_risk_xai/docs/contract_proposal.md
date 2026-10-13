# C3 contract proposal (not yet agreed)

**Status: proposal by the C3 owner.** `contracts/` is shared, and a change there needs a PR
reviewed by every affected owner (`contracts/README.md`). This file is the text for that PR.
`server/services/c3_risk_xai/src/c3_risk_xai/schemas.py` implements exactly this.

Both contracts are version **0.1**. Outputs are estimates and predictions, never diagnoses.

---

## 1. `patient_risk_profile` 0.1 (client → C3)

Sent to `POST /api/v1/risk/assess` on the gateway, which forwards it to C3 at `POST /v1/risk/assess`.
Every field is optional at the schema level, so C3 can report missing data instead of
rejecting the request. Unknown fields are rejected (HTTP 422).

| Field | Type | Unit / values | Required? | Notes |
|---|---|---|---|---|
| `schema_version` | string | `"0.1"` | optional (default `"0.1"`) | |
| `age` | number | years, 18-100 | **critical** | Missing → `insufficient_data` |
| `sex_male` | integer | 1 = male, 0 = female | optional | Median used if missing |
| `bmi` | number | kg/m², 12-70 | **critical** | The client computes it from height and weight |
| `systolic_bp` | number | mmHg, 70-260 | **critical** | |
| `diastolic_bp` | number | mmHg, 40-150 | **critical** | |
| `pulse_rate` | number | beats/min, 35-200 | optional | |
| `glucose_mmol` | number | mmol/L, 1.5-40 | optional | **If present, the glucose model is used** |
| `family_history_diabetes` | integer | 1 / 0 | optional | Parent or sibling |
| `family_history_hypertension` | integer | 1 / 0 | optional | Parent or sibling |
| `hypertensive` | integer | 1 / 0 | optional | Diagnosed high blood pressure |
| `cardiovascular_disease` | integer | 1 / 0 | optional | |
| `stroke` | integer | 1 / 0 | optional | |

Out-of-range values are not rejected with 422; C3 answers `invalid_input` and lists them.

### Wanted by the TAF, not in the model yet

The current model is trained on Bangladesh data that does not contain these, so they are
**not** accepted yet. Each needs a field name, unit and data source before it is added.

| TAF factor | Proposed field | Status |
|---|---|---|
| Cholesterol | `[INFORMATION REQUIRED]` | Not in any open South Asian dataset |
| Kidney disease | `[INFORMATION REQUIRED]` | Not in the training data |
| Liver disease | `[INFORMATION REQUIRED]` | Not in the training data |
| Body-weight change | `[INFORMATION REQUIRED]` | Not in the training data |
| Medication history / adherence | `[INFORMATION REQUIRED]` | Not in the training data |
| Physical activity, smoking | `[INFORMATION REQUIRED]` | Not in the training data |
| C1 nutrition summary | `[INFORMATION REQUIRED]` | Waits for the `meal_nutrition` contract |
| C2 glucose forecast | `[INFORMATION REQUIRED]` | Waits for the `glucose_forecast` contract |

### Example

```json
{
  "schema_version": "0.1",
  "age": 58, "sex_male": 1, "bmi": 27.8,
  "systolic_bp": 150, "diastolic_bp": 95, "pulse_rate": 84,
  "glucose_mmol": 9.8,
  "family_history_diabetes": 1, "family_history_hypertension": 1,
  "hypertensive": 1, "cardiovascular_disease": 0, "stroke": 0
}
```

---

## 2. `risk_assessment` 0.1 (C3 → client)

HTTP 200 for every assessed request, with one of three statuses. Fields that do not apply
to a status are **omitted** (not sent as `null`).

| Field | Type | When present | Meaning |
|---|---|---|---|
| `status` | `"ok"` \| `"insufficient_data"` \| `"invalid_input"` | always | |
| `disclaimer` | string | always | Must be shown on every result screen |
| `risk_category` | `"Low"` \| `"Moderate"` \| `"High"` | `ok` | Estimated risk band. Show label + icon, not colour alone |
| `referral` | string | `ok`, High only | Must be shown as a banner |
| `feature_set` | `"with_glucose"` \| `"without_glucose"` | `ok` | Which model answered |
| `model_used` | string | `ok` | e.g. `random_forest` |
| `model_version` | string (date) | `ok` | Training date of the model bundle |
| `data_complete` | boolean | `ok` | False when optional fields were filled with training medians |
| `imputed_fields` | string[] | `ok` | Which optional fields were filled |
| `missing_critical_fields` | string[] | `insufficient_data` | No band is returned |
| `problems` | string[] | `invalid_input` | Human-readable range errors |
| `explanation.shap[]` | object[] | `ok` | `feature, readable, factor_type, value, shap, direction` (top 5) |
| `explanation.lime[]` | object[] | `ok` | `rule, feature, readable, factor_type, value, weight, direction` |
| `explanation.lime_fidelity` | number | `ok` | LIME local fit R² |
| `explanation.agreement` | object | `ok` | `shap_top, lime_top, shared, overlap_ratio, meets_target` |
| `explanation.explanation_quality` | string | `ok` | `consistent`, or a `check: ...` warning |
| `explanation.explanation_text` | string | `ok` | Plain-language summary to show the patient |
| `debug` | object | research mode **and** `?debug=true` only | `risk_probability, risk_percent, thresholds` |

`factor_type` is `modifiable`, `not modifiable` or `medical history`. `direction` is
`increases risk` or `decreases risk`. SHAP/LIME values are contributions to the model's
estimate, not medical causes.

**Patient screens never show `debug`.** It is off unless the C3 server runs with
`C3_RESEARCH_MODE=true` (open item in `CLAUDE.md`: risk % vs band only).

Other HTTP codes: **422** wrong type or unknown field; **503** models not loaded;
**502** (from the gateway) C3 unreachable.

### Example: `ok` (real output of the trained model for the request above, shortened)

```json
{
  "status": "ok",
  "disclaimer": "Statistical risk estimate for self-management support. This is not a diagnosis and does not replace medical advice.",
  "risk_category": "High",
  "referral": "Because the estimate is in the High band, please arrange a blood test and a check-up with a doctor or a diabetes clinic.",
  "feature_set": "with_glucose",
  "model_used": "random_forest",
  "model_version": "2026-10-10",
  "data_complete": true,
  "imputed_fields": [],
  "explanation": {
    "shap": [
      {"feature": "hypertensive", "readable": "diagnosed high blood pressure",
       "factor_type": "medical history", "value": 1.0, "shap": 0.2646, "direction": "increases risk"}
    ],
    "lime": [
      {"rule": "hypertensive > 0.00", "feature": "hypertensive",
       "readable": "diagnosed high blood pressure", "factor_type": "medical history",
       "value": 1.0, "weight": 0.2863, "direction": "increases risk"}
    ],
    "lime_fidelity": 0.6888,
    "agreement": {"shap_top": ["age", "bmi", "diastolic_bp", "hypertensive", "pulse_rate"],
                  "lime_top": ["age", "bmi", "diastolic_bp", "glucose_mmol", "hypertensive"],
                  "shared": ["age", "bmi", "diastolic_bp", "hypertensive"],
                  "overlap_ratio": 0.8, "meets_target": true},
    "explanation_quality": "consistent",
    "explanation_text": "Your estimated risk band is High. Factors you can work on that raised it: body mass index (BMI), diastolic blood pressure. ..."
  }
}
```

### Example: `insufficient_data` (request with only `age` and `bmi`)

```json
{"status": "insufficient_data",
 "disclaimer": "Statistical risk estimate for self-management support. This is not a diagnosis and does not replace medical advice.",
 "missing_critical_fields": ["systolic_bp", "diastolic_bp"]}
```

### Example: `invalid_input` (BMI 500)

```json
{"status": "invalid_input",
 "disclaimer": "Statistical risk estimate for self-management support. This is not a diagnosis and does not replace medical advice.",
 "problems": ["bmi=500.0 is outside 12-70"]}
```

### Model status: `GET /api/v1/risk/status`

```json
{"model_loaded": true, "models": {"without_glucose": "logistic_regression", "with_glucose": "random_forest"}}
```
