# C2 Function 2 — Post-meal response indicator (method record)

> Research prototype. The indicator is a research-defined post-meal hyperglycaemic response
> indicator. It is not a diagnosis, not a clinically validated dietary-risk category and not a
> person-level diabetes risk score (C3's responsibility).

Recorded 2026-10-18. Decisions in this file were made by the C2 owner on 2026-10-18 unless marked
otherwise.

## 1. What the data does and does not contain

Checked against the raw CGMacros files (train participants) and the data dictionary:

- Per meal: timestamp, meal type, calories, carbohydrate, protein, fat, fibre, amount consumed (%)
  and a photo path. There are **no food names, no Sri Lankan foods and no GI/GL values**.
- All meals for about ten days are logged, so earlier same-day intake could be derived during
  training. The API receives one meal at a time, so cumulative daily intake is **not** a feature.
- Libre readings are genuine every 15 minutes; the minutes between them are linear interpolation.
  Long sensor gaps are also bridged by interpolation (up to 153 minutes in one training window).
- 979 photo-only rows (meal-end photos) have no meal type or nutrition and never create meals.
- Outliers are kept as logged (fibre up to 2199 g, amount consumed up to 700 %), as for the GRU.

## 2. Label

`above_180_within_4h` = 1 when **at least one genuine Libre reading from +15 to +240 minutes
(inclusive) after the meal is above 180 mg/dL**, else 0.

- 180 mg/dL matches the commonly used upper bound of the CGM target range and the ADA
  postprandial target. [INFORMATION REQUIRED: confirm the exact references with supervisors
  before citing them in the thesis.] The label is applied to all CGMacros participants
  (healthy, prediabetes and T2D) and to interstitial CGM, not capillary glucose.
- Only genuine readings count. Using the 15-minute grid instead changed 5 of 690 training
  labels because grid values near the window edge borrow height from readings outside it.
- The window must be covered: no gap over 20 minutes between consecutive readings or the window
  edges. Applied to both classes, so positives are not easier to keep than negatives (8 training
  meals excluded, 0 validation).
- **Isolation:** the existing clean dataset already drops meals followed by another logged meal
  within 4 hours. Labelling also drops meals *preceded* by one within 4 hours (241 train,
  59 validation), because their window overlaps the earlier meal's response. Windows of retained
  meals never overlap, and duplicate meal timestamps are rejected.

Code: `training/build_dietary_risk_labels.py` (tests: `tests/test_dietary_risk_labels.py`).
Output: `Desktop\CGMacros_C2_processed_premeal_fix\dietary_risk_labels\`.

## 3. Features (no observed post-meal glucose)

Defined once in `src/c2_glycemic_forecasting/trajectory_features.py` and used by both training
and the API:

- Nutrition: pre-meal glucose, calories, carbohydrate, protein, fat, fibre, carbohydrate share of
  energy (NaN when calories are 0).
- From the deployed single-step GRU forecast: predicted peak, peak time, peak change from
  pre-meal glucose, maximum rise, maximum rise rate, predicted iAUC.

A test changes every observed post-meal value and checks that no feature changes.

## 4. Leakage controls and protocol

- Fixed participant split (`training/cgmacros_participant_split.json`). The label script refuses
  the test split and never opens test participants' files. **The test set was not used.**
- Hyperparameters (fixed 12-configuration grid) and the decision threshold (max F1) were chosen
  with 5-fold participant-grouped cross-validation on training participants only.
- The deployed model (all-feature XGBoost) was fixed before validation. Comparators do not
  influence which model is deployed. Validation was scored once.
- Training is deterministic: a re-run reproduced the same model file (SHA-256 `54ae90a9…`).

Known biases:

- The GRU was trained on the same training participants, so its training forecasts are
  in-sample (train MAE 24.08 vs validation 24.91 mg/dL). Trajectory features on training meals
  may be slightly optimistic.
- The GRU checkpoint (epoch 47) was selected on validation loss, so validation is not fully
  untouched for the stacked pipeline. Only the test set is.

Code: `training/train_dietary_risk_xgb.py` (tests: `tests/test_dietary_risk_training.py`).
Output: `Desktop\CGMacros_C2_processed_premeal_fix\results_dietary_risk_xgb\`.

## 5. Results (actual, 2026-10-18)

Data: train 443 isolated meals (130 positive) from 30 participants; validation 116 isolated meals
(39 positive) from 7 participants, of whom only 4 have any positive meal.

Selected configuration (all features): max_depth 3, 100 rounds, min_child_weight 5, eta 0.05;
threshold 0.279.

| Validation (n = 116) | Precision | Recall | Specificity | F1 | ROC-AUC | Avg. precision |
|---|---|---|---|---|---|---|
| XGBoost, all features (deployed) | 0.561 | 0.590 | 0.766 | 0.575 | 0.764 | 0.667 |
| XGBoost, nutrition and pre-meal only | 0.543 | 0.487 | 0.792 | 0.514 | 0.750 | 0.667 |
| Rule: GRU predicted peak > 180 | 1.000 | 0.103 | 1.000 | 0.186 | 0.740 | 0.650 |
| No skill (positive rate) | | | | | 0.5 | 0.336 |

Deployed confusion matrix: TP 23, FP 18, FN 16, TN 59.

Cross-validation on training (out-of-fold, deployed configuration): ROC-AUC 0.850, average
precision 0.697, F1 0.716.

Sensitivity: on the 59 validation meals preceded by another meal within 4 hours (excluded above),
the deployed model reached ROC-AUC 0.665, precision 0.273, recall 0.600 (10 positives).

Interpretation:

- The classifier beats the no-skill rate and the GRU-peak rule. The GRU under-predicts peaks, so
  thresholding its forecast misses most positives.
- GRU trajectory features add little beyond nutrition and pre-meal glucose (ROC-AUC +0.014, equal
  average precision).
- Performance falls from cross-validation to validation. Validation positives are concentrated
  (18 of 39 from a single participant), so these estimates are uncertain. Participant-level
  intervals are in section 6.
- The API cannot know about earlier meals, and performance is worse for such meals.
- The classifier and the GRU can disagree. The threshold (0.279) favours recall, and the GRU
  under-predicts peaks, so a meal can be flagged while its predicted peak is below 180 mg/dL
  (seen in a live check: predicted peak 144 mg/dL, flagged). The client says a flag means a
  "possible" reading above 180 mg/dL and that the two models can differ.

## 6. Probability calibration evaluation (2026-10-19)

Question: is the deployed XGBoost output (`binary:logistic`) a usable probability of the target
event, i.e. at least one genuine Libre reading above 180 mg/dL from +15 to +240 minutes after the
meal? This is separate from the Boolean indicator: the 0.279 threshold was chosen to maximise F1
and is a decision threshold, not a calibrated risk boundary. Nothing below changes the model, its
threshold, the Boolean indicator or the API.

### 6.1 Training-only feasibility (Phase A, before validation was used)

On the 443 training meals (30 participants, 17 with any positive), out-of-fold scores from
participant-grouped cross-fitting, including nested re-selection of the hyperparameter grid:

- Selection optimism was negligible (nested and fixed-configuration scores correlated 0.987).
- Raw scores looked roughly calibrated at population level: Brier 0.137 (constant training rate
  0.207), calibration intercept 0.07, slope 0.87 (participant-bootstrap 95% interval 0.63–1.18).
- Cross-fitted Platt scaling and isotonic regression did not improve on the raw scores (Brier
  0.142 and 0.143; isotonic overfitted with slope 0.66). No calibrator was adopted.
- Population-level agreement hid large participant-level differences: 8 of 30 participants had an
  observed rate more than 0.2 away from their mean prediction.

### 6.2 Validation evaluation (Phase B, single pre-specified run)

Procedure (`training/evaluate_dietary_risk_calibration.py`, tests in
`tests/test_dietary_risk_calibration.py`):

- The deployed artefact is loaded through the service loader (SHA-256 `54ae90a9…` verified) and
  scored as the API scores it. Recomputed scores matched the stored validation predictions
  exactly, and the Boolean indicator equalled `score >= 0.279` for 116/116 meals.
- No calibrator was fitted and nothing was tuned. Validation labels were used once, for these
  metrics. Test participants were not loaded.
- Uncertainty: percentile intervals from 2,000 participant-cluster bootstrap resamples (seed 42;
  10 single-class resamples skipped) and a leave-one-participant-out analysis.
- Log loss clips predictions to [1e-6, 1 − 1e-6]; no prediction needed clipping.
- Model artefacts and the GRU checkpoint were hashed before and after the run and are unchanged.
  The report is aggregate only and is checked for identifiers before it is written.

Data: 116 isolated meals from 7 participants; 39 positive, 77 negative; 4 participants with any
positive meal. Reference: a constant prediction of the training positive rate (0.293).

| Calibration | Model | Constant 0.293 | Bootstrap 95% | Leave-one-out range |
|---|---|---|---|---|
| Brier score | 0.199 | 0.225 | 0.084 to 0.281 | 0.160 to 0.225 |
| Brier skill score | 0.114 | 0 | −0.298 to 0.467 | −0.008 to 0.287 |
| Log loss | 0.592 | 0.643 | 0.282 to 0.815 | 0.482 to 0.657 |
| Calibration intercept | 0.328 | | −0.992 to 1.443 | −0.342 to 0.561 |
| Calibration slope | 0.561 | | 0.108 to 1.269 | 0.459 to 0.768 |

Mean predicted 0.295 vs observed 0.336.

| Reliability (equal-size bins) | Meals | Mean predicted | Observed rate (meal-level Wilson 95%) |
|---|---|---|---|
| Lowest third | 39 | 0.055 | 0.128 (0.056–0.267) |
| Middle third | 39 | 0.156 | 0.308 (0.186–0.464) |
| Highest third | 38 | 0.684 | 0.579 (0.422–0.721) |

Discrimination (ranking only; not calibration): ROC-AUC 0.764 (bootstrap 0.556–0.921), average
precision 0.667 (0.201–0.899; constant baseline 0.336).

Exploratory criteria proposed in Phase A (not clinical or universal standards): Brier skill lower
95% bound above 0 — not met; calibration-intercept interval includes 0 — met; slope between 0.7
and 1.3 — not met (0.561).

### 6.3 Interpretation

- The validation scores are too extreme (slope 0.56; six of seven leave-one-out estimates are
  below 0.7). They underpredict in the lower two thirds and overpredict in the top third. This
  is the opposite of what the training cross-fit suggested (slope 0.87), so the training-only
  evidence did not transfer to new participants.
- The model improves on the constant training rate by a small margin in point estimates, but the
  participant-level interval for Brier skill includes values below 0.
- The intercept interval including 0 reflects how wide the interval is with seven participants,
  not evidence of good calibration.
- Recalibrating on these validation outcomes would turn the only evaluation set into a training
  set and was deliberately not done.

Limitations: seven validation participants (four with a positive meal), so the bootstrap over
clusters is unstable and can understate uncertainty; the GRU checkpoint was selected on validation
loss, so validation is not fully untouched for this pipeline; meals preceded by another meal within
four hours were excluded; population-level calibration says nothing about an individual; data are
CGMacros, not a Sri Lankan clinical validation cohort.

**Conclusion:** the evidence does not support exposing the XGBoost output as a probability or a
0–100 score. The Boolean indicator remains the only output. Any future probability would need new
data for recalibration and evaluation (not the sealed test set used to repair this result) and
supervisor approval.

Reproduce (from the repository root; writes
`Desktop\CGMacros_C2_processed_premeal_fix\results_dietary_risk_calibration\calibration_report.json`
and refuses to overwrite it):

```bash
uv run python server/services/c2_glycemic_forecasting/training/evaluate_dietary_risk_calibration.py
```

## 7. Decisions still required

1. Supervisor confirmation of the label threshold, its references and its use for non-diabetic
   participants.
2. Whether C3 should receive a probability. Section 6 found the current output miscalibrated on
   validation, so none is returned.
3. **TAF composite dietary risk score** (meal timing, carbohydrate load, cumulative daily intake):
   not implemented. It needs justified weights, meal time in the request and a meal-history
   source. No weights were invented.
4. **Sri Lankan GI/GL**: CGMacros has no food identities, so GI/GL cannot be linked to training
   meals. A source with licensing and a linking method is still needed.
5. When to evaluate once on the sealed test participants.
