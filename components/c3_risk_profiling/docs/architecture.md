# Architecture - Component 3

## Simple view

```
Patient data (questionnaire + clinical, optional glucose)
          |
          v
   Input validation          <- reject impossible values (e.g. BMI 500)
          |
          v
   Completeness check        <- missing age/BMI/BP: "insufficient_data", NO band
          |                     other gaps: training median, listed in the output
          v
   Model choice              <- glucose given ? "with_glucose" : "without_glucose"
          |
          v
   Risk model                <- selected by cross-validated PR-AUC
          |                     (logistic regression / random forest / XGBoost)
          v
   Calibration               <- Platt scaling fitted on out-of-fold scores
          |
          v
   Risk band                 <- data-driven cut-offs (90% sensitivity / 90% specificity)
          |                     FUNCTION 1 OUTPUT (+ referral note for High)
          v
   SHAP  +  LIME             <- contributions and local surrogate (+ LIME fit R²)
          |
          v
   Agreement + quality flag  <- top-5 overlap vs the proposal's 60% target
          |
          v
   Plain-language summary    <- modifiable vs not-modifiable factors
          |                     FUNCTION 2 OUTPUT
          v
   Streamlit demo UI (PP1)  /  FastAPI service in server/services/c3_risk_xai (PP2)
```

## Training pipeline

```
DiaBD + Narsingdi (Bangladesh)  --south_asia_dataset-->  harmonised table
        |
        v  stratified 80/20 split (DiaBD); 20% REAL test set is locked away
        |
   5-fold CV on the training split; inside every fold:
        medians + synthetic generator fitted on that fold only -> real+synthetic fit
        |
        v
   out-of-fold scores -> model choice, calibration, band cut-offs
        |
        v
   refit on full training split (real + synthetic) -> scored once on the real test set
```

## Where each block lives

| Block | File | PP1 status |
|---|---|---|
| Download with provenance | `src/external_data.py` | Done |
| Harmonise + plausibility | `src/south_asia_dataset.py` | Done |
| Load and inspect | `src/data_loader.py` | Done |
| Split | `src/preprocess.py` | Done |
| Synthetic generator | `src/synthetic.py` | Done |
| Train, calibrate, bands | `src/train.py` | Done |
| Predict (Function 1) | `src/predict.py` | Done |
| Explain (Function 2) | `src/explain.py` | Done |
| Evidence figures | `src/evidence.py` | Done |
| Demo UI | `app/streamlit_app.py` | Done |
| DHS engine | not yet created | PP2 |
| FastAPI service | `server/services/c3_risk_xai` (team scaffold) | PP2 |

## Integration with the other components

Do not implement the other members' modules. Agree the **contract** only.

```
  C1 Food Recognition  --(nutrition features)-->  |
                                                  |
  C2 Glycemic Forecast --(forecast features)-->   |  C3 Risk Profiling
                                                  |  + Explainable AI
  Patient questionnaire + clinical input ------>  |
                                                  |
                                                  +--(risk, DHS, explanations)--> C4 Mobile App
```

### Input C3 accepts today (`predict_risk`)

```json
{
  "age": 58, "sex_male": 1, "bmi": 27.8,
  "systolic_bp": 150, "diastolic_bp": 95, "pulse_rate": 84,
  "glucose_mmol": 9.8,
  "family_history_diabetes": 1, "family_history_hypertension": 1,
  "hypertensive": 1, "cardiovascular_disease": 0, "stroke": 0
}
```

`glucose_mmol` is optional. In PP2 the C1 nutrition and C2 forecast fields are added
to this contract in `contracts/`.

### Output C3 produces (`explain_patient`)

```json
{
  "prediction": {
    "status": "ok",
    "risk_category": "High",
    "risk_probability": 0.5657,
    "feature_set": "with_glucose",
    "model_used": "random_forest",
    "thresholds": {"low_max": 0.0259, "high_min": 0.1345},
    "imputed_fields": [],
    "data_complete": true,
    "referral": "Because the estimate is in the High band, ...",
    "disclaimer": "... not a diagnosis ..."
  },
  "shap": [{"feature": "hypertensive", "factor_type": "medical history",
            "shap": 0.2646, "direction": "increases risk"}],
  "lime": [{"rule": "hypertensive > 0.00", "weight": 0.2863}],
  "lime_fidelity": 0.69,
  "agreement": {"overlap_ratio": 0.8, "meets_target": true},
  "explanation_quality": "consistent",
  "explanation_text": "Your estimated risk band is High. ..."
}
```

Other statuses: `insufficient_data` (lists `missing_critical_fields`, no band) and
`invalid_input` (lists `problems`).

**If Component 3 is removed**, the system can still recognise food and forecast
glucose, but nobody is told what their overall diabetes risk is, which factors
drive it, or why. The explainable decision layer disappears entirely.
