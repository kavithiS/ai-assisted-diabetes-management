# Architecture - Component 3

## Simple view

```
Patient data (questionnaire + clinical)
          |
          v
   Input validation          <- reject impossible values, report missing fields
          |
          v
   Preprocessing             <- same transforms as training, no leakage
          |
          v
   Feature alignment         <- exact column order the model expects
          |
          v
   Risk prediction model     <- logistic regression / random forest / XGBoost
          |
          v
   Risk probability + band   <- FUNCTION 1 OUTPUT
          |
          v
   SHAP  +  LIME             <- contributions and local surrogate
          |
          v
   Agreement check           <- do the two methods pick the same factors?
          |
          v
   Plain-language explanation  <- FUNCTION 2 OUTPUT
          |
          v
   Streamlit demo UI (PP1)  /  FastAPI service (PP2)
```

## Where each block lives

| Block | File | PP1 status |
|---|---|---|
| Load and inspect | `src/data_loader.py` | Done |
| Clean and split | `src/preprocess.py` | Done |
| Train and compare | `src/train.py` | Done |
| Predict (Function 1) | `src/predict.py` | Done |
| Explain (Function 2) | `src/explain.py` | Done |
| Demo UI | `app/streamlit_app.py` | Done |
| DHS engine | not yet created | PP2 |
| FastAPI service | not yet created | PP2 |

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

### Input contract C3 expects (placeholder - confirm with the team)

```json
{
  "patient_id": "string",
  "questionnaire": { "Age": 9, "Sex": 1, "Smoker": 0, "PhysActivity": 1 },
  "clinical":      { "BMI": 29.4, "HighBP": 1, "HighChol": 1 },
  "nutrition_c1":  { "status": "pending", "source": "Component 1" },
  "forecast_c2":   { "status": "pending", "source": "Component 2" }
}
```

### Output contract C3 produces

```json
{
  "risk_probability": 0.52,
  "risk_category": "Moderate",
  "top_factors": [
    { "feature": "HighBP", "readable": "high blood pressure",
      "contribution": 0.0729, "direction": "increases risk" }
  ],
  "xai_agreement": 0.6,
  "explanation_text": "...",
  "data_complete": true,
  "disclaimer": "Not a diagnosis."
}
```

**If Component 3 is removed**, the system can still recognise food and forecast
glucose, but nobody is told what their overall diabetes risk is, which factors
drive it, or why. The explainable decision layer disappears entirely.
