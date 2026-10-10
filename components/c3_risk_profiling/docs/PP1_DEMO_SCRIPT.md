# PP1 demo script - Component 3

About 6 minutes of live demo inside a 10-12 minute slot. Every number below comes
from `outputs/reports/` and was produced by the code in this repository.

## Before the panel (5 minutes)

```powershell
cd C:\Users\ALFARES\Desktop\c3-risk-profiling\components\c3_risk_profiling
.venv\Scripts\activate
python -m pytest -q                  # expect: 17 passed
streamlit run app/streamlit_app.py   # opens http://localhost:8501
```

Click **Assess risk** once before the panel arrives, so SHAP and LIME are warm.
Keep the backup video and `outputs/figures/` open in case the live demo fails.

## Live sequence

1. **Repository (20 s).** Show `src/`: `predict.py` is Function 1 and `explain.py` is Function 2.
2. **Data (40 s).** Run `python -m src.data_loader`.
   - Say: "Only South Asian data. DiaBD has 5,288 Bangladeshi adults, 6.5% diabetic.
     The Narsingdi hospital file is a second site. It had 1,065 rows, but only 496 were unique."
   - Say: "No open Sri Lankan individual-level data exists. These are Bangladesh findings."
3. **Function 1 (60 s).** In the app, choose **Higher-risk example** and click **Assess risk**.
   - Show the High band and the referral note.
   - Untick **I have a recent blood glucose result**. The app switches to the questionnaire-only model.
   - Choose **Lower-risk example** to show the Low band.
4. **Function 2 (90 s).**
   - Read the plain-language summary, noting the split between modifiable and background factors.
   - Point to the SHAP chart, then the LIME table, the 80% agreement and the LIME fit R².
   - Say: "Disagreement is reported, not hidden. A weak fit triggers a warning."
5. **Safety (20 s).** Point at the disclaimer. Open the **Researcher view** expander and
   say the probability is kept out of the patient view.
6. **Evidence (60 s).** Open the **Model evidence** tab and show:
   - the model table: 5-fold CV and the real test set, PR-AUC not accuracy;
   - the risk-band chart: Low 1.1% diabetic vs High 29.0% (with glucose);
   - the calibration chart, where Brier drops from 0.068 to 0.051.
7. **Tests (20 s).** Show the `python -m pytest -v` output: 17 passed, run without the dataset.
8. **Next (10 s).** DHS, C1/C2 integration through FastAPI, and Sri Lankan questionnaire data after ethics approval.

## Key numbers (real test set, 1,058 people never used in training)

| | Without glucose | With glucose |
|---|---|---|
| Selected model | logistic regression | random forest |
| 5-fold CV ROC-AUC | 0.814 | 0.871 |
| Test ROC-AUC | 0.779 | 0.853 |
| Test PR-AUC (base rate 0.065) | 0.220 | 0.341 |
| % diabetic in Low / Moderate / High | 1.8 / 6.5 / 24.4 | 1.1 / 7.3 / 29.0 |
| Median SHAP-LIME top-5 overlap (30 patients) | 0.80 | 0.80 |
| Median LIME fit R² | 0.74 | 0.33 |

Synthetic augmentation: fidelity SMD 0.012, 0 copies of real people. It made no
meaningful ROC-AUC difference, and random forest recall with glucose rose from 0.43
to 0.51. Second site: without glucose the model drops to ROC-AUC 0.54-0.58 on
Narsingdi, which is the case for local validation.

## Likely questions

- **"Why not accuracy?"** Only 6.5% are diabetic. Always answering "no" scores 93.5%.
  So the model is chosen by PR-AUC and recall is reported.
- **"Where do the bands come from?"** From cross-validated training predictions,
  never the test set. Low keeps 90% of diabetic people above it. High is above what
  90% of non-diabetic people score. They are pending clinical review.
- **"Why two models?"** Many users will not have a blood test. The app uses glucose
  only when it is given, instead of guessing it.
- **"Is the synthetic data used for testing?"** No. The generator only sees the
  training rows, and every reported number is on real people.
- **"Why is LIME's fit lower for the glucose model?"** The random forest is more
  non-linear, so a straight-line local surrogate fits it less well. The app flags weak fits.
- **"Why not Sri Lankan data?"** None is openly available. STEPS and SLHAS are on
  request, and our own questionnaire needs ethics approval first.
